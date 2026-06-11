from __future__ import annotations

import os
from typing import Any, List

import numpy as np
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from database import get_db
import models

router = APIRouter(prefix="/rag", tags=["RAG – Consulta Inteligente"])

class RagRequest(BaseModel):
    pergunta: str


class RagResponse(BaseModel):
    resposta: str
    modo: str
    documentos_usados: int

# Modelo de embedding disponível para esta chave de API
_EMBEDDING_MODEL = "gemini-embedding-2"

def _get_client() -> tuple[genai.Client, str]:
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key.strip():
        raise HTTPException(500, "GEMINI_API_KEY não configurada.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    # Usa types.HttpOptions — gemini-embedding-2 está disponível em v1beta
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    return client, model

def _build_documents(db: Session) -> List[str]:
    """Converte os registros do banco em documentos textuais para RAG."""
    docs: List[str] = []

    # Fornecedores
    for f in db.query(models.Fornecedor).all():
        docs.append(
            f"[FORNECEDOR id={f.id}] Razão Social: {f.razao_social} | "
            f"Fantasia: {f.fantasia or '-'} | CNPJ: {f.cnpj} | "
            f"Status: {'Ativo' if f.ativo else 'Inativo'}"
        )

    # Clientes
    for c in db.query(models.Cliente).all():
        docs.append(
            f"[CLIENTE id={c.id}] Nome: {c.nome} | CPF/CNPJ: {c.cpf_cnpj} | "
            f"Email: {c.email or '-'} | Telefone: {c.telefone or '-'} | "
            f"Status: {'Ativo' if c.ativo else 'Inativo'}"
        )

    # Faturados
    for f in db.query(models.Faturado).all():
        docs.append(
            f"[FATURADO id={f.id}] Nome: {f.nome_completo} | CPF: {f.cpf} | "
            f"Status: {'Ativo' if f.ativo else 'Inativo'}"
        )

    # Tipos de Despesa
    for t in db.query(models.TipoDespesa).all():
        docs.append(
            f"[TIPO_DESPESA id={t.id}] Nome: {t.nome} | "
            f"Descrição: {t.descricao or '-'} | Status: {'Ativo' if t.ativo else 'Inativo'}"
        )

    # Tipos de Receita
    for t in db.query(models.TipoReceita).all():
        docs.append(
            f"[TIPO_RECEITA id={t.id}] Nome: {t.nome} | "
            f"Descrição: {t.descricao or '-'} | Status: {'Ativo' if t.ativo else 'Inativo'}"
        )

    # Contas a Pagar (com parcelas e classificações)
    contas_pagar = (
        db.query(models.ContasPagar)
        .options(
            joinedload(models.ContasPagar.parcelas),
            joinedload(models.ContasPagar.classificacoes).joinedload(models.ClassificacaoPagar.tipo_despesa),
            joinedload(models.ContasPagar.fornecedor),
            joinedload(models.ContasPagar.faturado),
        )
        .all()
    )
    for cp in contas_pagar:
        fornecedor_nome = cp.fornecedor.razao_social if cp.fornecedor else "-"
        faturado_nome = cp.faturado.nome_completo if cp.faturado else "-"
        parcelas_txt = "; ".join(
            f"Parcela {p.numero} vence {p.data_vencimento} R${p.valor:.2f} {'(PAGO)' if p.pago else '(ABERTO)'}"
            for p in sorted(cp.parcelas, key=lambda x: x.numero)
        )
        classificacoes_txt = ", ".join(c.tipo_despesa.nome for c in cp.classificacoes if c.tipo_despesa)
        docs.append(
            f"[CONTA_PAGAR id={cp.id}] NF: {cp.numero_nf or '-'} | "
            f"Emissão: {cp.data_emissao} | Valor Total: R${cp.valor_total:.2f} | "
            f"Fornecedor: {fornecedor_nome} | Faturado: {faturado_nome} | "
            f"Descrição: {cp.descricao or '-'} | "
            f"Classificações: {classificacoes_txt or '-'} | "
            f"Parcelas: [{parcelas_txt}] | "
            f"Status: {'Ativo' if cp.ativo else 'Inativo'}"
        )

    # Contas a Receber (com parcelas e classificações)
    contas_receber = (
        db.query(models.ContasReceber)
        .options(
            joinedload(models.ContasReceber.parcelas),
            joinedload(models.ContasReceber.classificacoes).joinedload(models.ClassificacaoReceber.tipo_receita),
            joinedload(models.ContasReceber.cliente),
        )
        .all()
    )
    for cr in contas_receber:
        cliente_nome = cr.cliente.nome if cr.cliente else "-"
        parcelas_txt = "; ".join(
            f"Parcela {p.numero} vence {p.data_vencimento} R${p.valor:.2f} {'(RECEBIDO)' if p.recebido else '(ABERTO)'}"
            for p in sorted(cr.parcelas, key=lambda x: x.numero)
        )
        classificacoes_txt = ", ".join(c.tipo_receita.nome for c in cr.classificacoes if c.tipo_receita)
        docs.append(
            f"[CONTA_RECEBER id={cr.id}] "
            f"Emissão: {cr.data_emissao} | Valor Total: R${cr.valor_total:.2f} | "
            f"Cliente: {cliente_nome} | "
            f"Descrição: {cr.descricao or '-'} | "
            f"Classificações: {classificacoes_txt or '-'} | "
            f"Parcelas: [{parcelas_txt}] | "
            f"Status: {'Ativo' if cr.ativo else 'Inativo'}"
        )

    return docs

_SYSTEM_PROMPT = """Você é um assistente financeiro especializado em análise de dados de contas a pagar e receber.
Responda sempre em português brasileiro, de forma clara, objetiva e bem formatada.
Use listas, tabelas e destaques quando for útil para a compreensão.
Se os dados não forem suficientes para responder, informe isso claramente.
Não invente informações — baseie-se apenas no contexto fornecido."""


def _call_llm(client: genai.Client, model: str, pergunta: str, contexto: str) -> str:
    prompt = f"""{_SYSTEM_PROMPT}

=== DADOS DO BANCO ===
{contexto}

=== PERGUNTA DO USUÁRIO ===
{pergunta}

=== RESPOSTA ==="""
    resp = client.models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return (resp.text or "").strip()

@router.post("/simples", response_model=RagResponse)
def rag_simples(body: RagRequest, db: Session = Depends(get_db)):
    """RAG Simples: todos os dados do banco são passados como contexto ao LLM."""
    client, model = _get_client()

    documentos = _build_documents(db)
    if not documentos:
        raise HTTPException(404, "Nenhum dado encontrado no banco de dados.")

    contexto = "\n".join(documentos)

    try:
        resposta = _call_llm(client, model, body.pergunta, contexto)
    except Exception as e:
        raise HTTPException(502, f"Erro ao chamar o modelo: {type(e).__name__}: {e}")

    return RagResponse(
        resposta=resposta,
        modo="simples",
        documentos_usados=len(documentos),
    )

_TOP_K = 15  # número máximo de documentos relevantes a passar ao LLM


def _embed_batch(client: genai.Client, texts: List[str]) -> np.ndarray:
    """Gera embeddings para uma lista de textos usando a API do Gemini."""
    result = client.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return np.array([e.values for e in result.embeddings], dtype=np.float32)


def _embed_query(client: genai.Client, query: str) -> np.ndarray:
    """Gera embedding para a query do usuário."""
    result = client.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=[query],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return np.array(result.embeddings[0].values, dtype=np.float32)


def _cosine_similarity(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """Calcula a similaridade cosseno entre a query e todos os documentos."""
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    doc_norms = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-10)
    return doc_norms @ query_norm


@router.post("/embeddings", response_model=RagResponse)
def rag_embeddings(body: RagRequest, db: Session = Depends(get_db)):
    """RAG Embeddings: vetoriza documentos e pergunta, seleciona top-K mais relevantes."""
    client, model = _get_client()

    documentos = _build_documents(db)
    if not documentos:
        raise HTTPException(404, "Nenhum dado encontrado no banco de dados.")

    try:
        # Gera embeddings para todos os documentos
        doc_vecs = _embed_batch(client, documentos)

        # Gera embedding da query
        query_vec = _embed_query(client, body.pergunta)

        # Calcula similaridade e seleciona top-K
        scores = _cosine_similarity(query_vec, doc_vecs)
        top_k = min(_TOP_K, len(documentos))
        top_indices = np.argsort(scores)[::-1][:top_k]

        docs_relevantes = [documentos[i] for i in top_indices]
        contexto = "\n".join(docs_relevantes)

        resposta = _call_llm(client, model, body.pergunta, contexto)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Erro no RAG Embeddings: {type(e).__name__}: {e}")

    return RagResponse(
        resposta=resposta,
        modo="embeddings",
        documentos_usados=len(docs_relevantes),
    )
