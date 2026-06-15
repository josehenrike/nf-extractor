from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from groq import Groq
from rank_bm25 import BM25Okapi

from database import get_db
import models

router = APIRouter(prefix="/rag", tags=["RAG – Consulta Inteligente"])

class RagRequest(BaseModel):
    pergunta: str
    top_k: int = 15

class RagResponse(BaseModel):
    resposta: str
    modo: str
    documentos_usados: int
    total_documentos: int
    cache_hit: bool = False
    tempo_ms: float = 0.0

def _cfg() -> dict:
    load_dotenv(override=False)
    return {
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "llm_model":    os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    }

_MAX_DOC_CHARS = 1000
_MAX_TOP_K     = 10

def _build_documents(db: Session) -> List[str]:
    docs: List[str] = []
    for f in db.query(models.Fornecedor).all():
        docs.append(f"[FORNECEDOR] {f.razao_social} | Fantasia: {f.fantasia or '-'} | CNPJ: {f.cnpj}")
    for c in db.query(models.Cliente).all():
        docs.append(f"[CLIENTE] {c.nome} | CPF/CNPJ: {c.cpf_cnpj}")
    for f in db.query(models.Faturado).all():
        docs.append(f"[FATURADO] {f.nome_completo} | CPF: {f.cpf}")
    
    contas_pagar = db.query(models.ContasPagar).options(joinedload(models.ContasPagar.parcelas), joinedload(models.ContasPagar.classificacoes).joinedload(models.ClassificacaoPagar.tipo_despesa), joinedload(models.ContasPagar.fornecedor), joinedload(models.ContasPagar.faturado)).all()
    for cp in contas_pagar:
        forn_nome = cp.fornecedor.razao_social if cp.fornecedor else "-"
        parcelas_txt = "; ".join(f"P{p.numero} vence {p.data_vencimento} R${p.valor:.2f} {'[PAGO]' if p.pago else '[ABERTO]'}" for p in cp.parcelas)
        docs.append(f"[CONTA_PAGAR id={cp.id}] Fornecedor:{forn_nome} | Emissão:{cp.data_emissao} | Total:R${cp.valor_total:.2f} | Parcelas:[{parcelas_txt}] | Descr:{cp.descricao or '-'}")

    contas_receber = db.query(models.ContasReceber).options(joinedload(models.ContasReceber.parcelas), joinedload(models.ContasReceber.classificacoes).joinedload(models.ClassificacaoReceber.tipo_receita), joinedload(models.ContasReceber.cliente)).all()
    for cr in contas_receber:
        cli_nome = cr.cliente.nome if cr.cliente else "-"
        parcelas_txt = "; ".join(f"P{p.numero} vence {p.data_vencimento} R${p.valor:.2f} {'[RECEBIDO]' if p.recebido else '[ABERTO]'}" for p in cr.parcelas)
        docs.append(f"[CONTA_RECEBER id={cr.id}] Cliente:{cli_nome} | Emissão:{cr.data_emissao} | Total:R${cr.valor_total:.2f} | Parcelas:[{parcelas_txt}] | Descr:{cr.descricao or '-'}")

    return docs

def _build_resumo(db: Session) -> str:
    cp_all = db.query(models.ContasPagar).options(joinedload(models.ContasPagar.parcelas), joinedload(models.ContasPagar.fornecedor)).all()
    cr_all = db.query(models.ContasReceber).options(joinedload(models.ContasReceber.parcelas), joinedload(models.ContasReceber.cliente)).all()
    cp_total = sum(c.valor_total for c in cp_all)
    cr_total = sum(c.valor_total for c in cr_all)
    return f"RESUMO: {len(cp_all)} contas a pagar (R${cp_total:.2f}). {len(cr_all)} contas a receber (R${cr_total:.2f})."

_SYSTEM_PROMPT = """Você é um assistente financeiro. Responda a pergunta com base nos DADOS RELEVANTES (pesquisa do banco). Seja exato."""

def _call_llm(model_name: str, pergunta: str, resumo: str, docs_relevantes: List[str]) -> str:
    cfg = _cfg()
    client = Groq(api_key=cfg["groq_api_key"])
    docs_txt = "\n".join(docs_relevantes)
    user_msg = f"{resumo}\n\n=== DADOS RELEVANTES ===\n{docs_txt}\n\nPERGUNTA: {pergunta}"
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=1500,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(502, f"Erro ao chamar LLM (Groq): {e}")

@router.post("/embeddings", response_model=RagResponse)
def rag_embeddings(body: RagRequest, db: Session = Depends(get_db)):
    t0 = time.perf_counter()
    documentos = _build_documents(db)
    if not documentos:
        raise HTTPException(404, "Nenhum dado.")
    
    # BM25 Search (Instantâneo e local)
    tokenized_corpus = [doc.lower().split() for doc in documentos]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = body.pergunta.lower().split()
    
    top_k = min(max(1, body.top_k), _MAX_TOP_K)
    docs_selecionados = bm25.get_top_n(tokenized_query, documentos, n=top_k)
    
    resposta = _call_llm(_cfg()["llm_model"], body.pergunta, _build_resumo(db), docs_selecionados)
    
    return RagResponse(
        resposta=resposta,
        modo="BM25 Search + Groq (Anti-Limite)",
        documentos_usados=len(docs_selecionados),
        total_documentos=len(documentos),
        tempo_ms=round((time.perf_counter() - t0)*1000, 1),
    )

@router.post("/simples", response_model=RagResponse)
def rag_simples(body: RagRequest, db: Session = Depends(get_db)):
    return rag_embeddings(body, db)
