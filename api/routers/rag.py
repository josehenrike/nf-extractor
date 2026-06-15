from __future__ import annotations

"""
RAG – Consulta Inteligente com cache de embeddings + pré-cálculo de dados.

Estratégia:
  • Todos os documentos do banco são indexados UMA vez (cache SHA-256).
  • Além dos docs, uma seção de RESUMO ESTATÍSTICO é pré-calculada no Python
    e enviada ao LLM — ele não precisa calcular, só reportar.
  • O LLM recebe: resumo geral + docs relevantes selecionados por embedding.
"""

import hashlib
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import ollama
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from database import get_db
import models

router = APIRouter(prefix="/rag", tags=["RAG – Consulta Inteligente"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class RagRequest(BaseModel):
    pergunta: str
    top_k: int = 15          # quantos docs relevantes enviar ao LLM


class RagResponse(BaseModel):
    resposta: str
    modo: str
    documentos_usados: int
    total_documentos: int
    cache_hit: bool = False
    tempo_ms: float = 0.0


# ─── Configurações ────────────────────────────────────────────────────────────

def _cfg() -> dict:
    load_dotenv(override=False)
    return {
        "host":        os.getenv("OLLAMA_HOST",        "http://ollama:11434"),
        "llm_model":   os.getenv("OLLAMA_LLM_MODEL",   "llama3.2"),
        "embed_model": os.getenv("OLLAMA_EMBED_MODEL",  "nomic-embed-text"),
    }


_MAX_DOC_CHARS = 700   # chars por documento antes de truncar
_MAX_TOP_K     = 200   # limite máximo de top_k


# ─── Cache ────────────────────────────────────────────────────────────────────

@dataclass
class _EmbeddingCache:
    docs_hash:  str                  = ""
    documentos: List[str]            = field(default_factory=list)
    vectors:    Optional[np.ndarray] = None
    built_at:   float                = 0.0
    _query_cache: dict               = field(default_factory=dict)

    def is_valid(self, h: str) -> bool:
        return self.vectors is not None and self.docs_hash == h

    def update(self, documentos: List[str], vectors: np.ndarray, h: str) -> None:
        self.documentos   = documentos
        self.vectors      = vectors
        self.docs_hash    = h
        self.built_at     = time.time()
        self._query_cache = {}
        print(f"[RAG:cache] Índice criado — {len(documentos)} documentos.")

    def invalidate(self) -> None:
        self.docs_hash = ""
        self.documentos = []
        self.vectors = None
        self.built_at = 0.0
        self._query_cache = {}
        print("[RAG:cache] Índice invalidado.")

    def get_query_vec(self, pergunta: str) -> Optional[np.ndarray]:
        return self._query_cache.get(pergunta)

    def set_query_vec(self, pergunta: str, vec: np.ndarray) -> None:
        if len(self._query_cache) >= 256:
            del self._query_cache[next(iter(self._query_cache))]
        self._query_cache[pergunta] = vec


_cache = _EmbeddingCache()


def _docs_hash(documentos: List[str]) -> str:
    return hashlib.sha256("\n".join(documentos).encode()).hexdigest()


def _get_ollama_client() -> ollama.Client:
    return ollama.Client(host=_cfg()["host"])


# ─── Construção de documentos ─────────────────────────────────────────────────

def _build_documents(db: Session) -> List[str]:
    """Converte todos os registros em documentos textuais para RAG."""
    docs: List[str] = []

    for f in db.query(models.Fornecedor).all():
        docs.append(
            f"[FORNECEDOR id={f.id}] {f.razao_social} | "
            f"Fantasia: {f.fantasia or '-'} | CNPJ: {f.cnpj} | "
            f"Status: {'Ativo' if f.ativo else 'Inativo'}"
        )

    for c in db.query(models.Cliente).all():
        docs.append(
            f"[CLIENTE id={c.id}] {c.nome} | CPF/CNPJ: {c.cpf_cnpj} | "
            f"Email: {c.email or '-'} | Tel: {c.telefone or '-'} | "
            f"Status: {'Ativo' if c.ativo else 'Inativo'}"
        )

    for f in db.query(models.Faturado).all():
        docs.append(
            f"[FATURADO id={f.id}] {f.nome_completo} | CPF: {f.cpf} | "
            f"Status: {'Ativo' if f.ativo else 'Inativo'}"
        )

    for t in db.query(models.TipoDespesa).all():
        docs.append(
            f"[TIPO_DESPESA id={t.id}] {t.nome} | "
            f"Descrição: {t.descricao or '-'} | Status: {'Ativo' if t.ativo else 'Inativo'}"
        )

    for t in db.query(models.TipoReceita).all():
        docs.append(
            f"[TIPO_RECEITA id={t.id}] {t.nome} | "
            f"Descrição: {t.descricao or '-'} | Status: {'Ativo' if t.ativo else 'Inativo'}"
        )

    contas_pagar = (
        db.query(models.ContasPagar)
        .options(
            joinedload(models.ContasPagar.parcelas),
            joinedload(models.ContasPagar.classificacoes).joinedload(
                models.ClassificacaoPagar.tipo_despesa
            ),
            joinedload(models.ContasPagar.fornecedor),
            joinedload(models.ContasPagar.faturado),
        )
        .all()
    )
    for cp in contas_pagar:
        fornecedor_nome = cp.fornecedor.razao_social if cp.fornecedor else "-"
        fornecedor_cnpj = cp.fornecedor.cnpj          if cp.fornecedor else "-"
        faturado_nome   = cp.faturado.nome_completo   if cp.faturado   else "-"
        faturado_cpf    = cp.faturado.cpf             if cp.faturado   else "-"
        pagas  = sum(1 for p in cp.parcelas if p.pago)
        total  = len(cp.parcelas)
        valor_pago   = sum(p.valor for p in cp.parcelas if p.pago)
        valor_aberto = sum(p.valor for p in cp.parcelas if not p.pago)
        parcelas_txt = "; ".join(
            f"P{p.numero} vence {p.data_vencimento} R${p.valor:.2f} {'[PAGO]' if p.pago else '[ABERTO]'}"
            for p in sorted(cp.parcelas, key=lambda x: x.numero)
        )
        classificacoes_txt = ", ".join(
            c.tipo_despesa.nome for c in cp.classificacoes if c.tipo_despesa
        )
        docs.append(
            f"[CONTA_PAGAR id={cp.id}] NF:{cp.numero_nf or '-'} | "
            f"Emissão:{cp.data_emissao} | Total:R${cp.valor_total:.2f} | "
            f"Pago:R${valor_pago:.2f} | Aberto:R${valor_aberto:.2f} | "
            f"Fornecedor:{fornecedor_nome}(CNPJ:{fornecedor_cnpj}) | "
            f"Faturado:{faturado_nome}(CPF:{faturado_cpf}) | "
            f"Descr:{cp.descricao or '-'} | Class:{classificacoes_txt or '-'} | "
            f"Parcelas({pagas}/{total} pagas):[{parcelas_txt}] | "
            f"Status:{'Ativo' if cp.ativo else 'Inativo'}"
        )

    contas_receber = (
        db.query(models.ContasReceber)
        .options(
            joinedload(models.ContasReceber.parcelas),
            joinedload(models.ContasReceber.classificacoes).joinedload(
                models.ClassificacaoReceber.tipo_receita
            ),
            joinedload(models.ContasReceber.cliente),
        )
        .all()
    )
    for cr in contas_receber:
        cliente_nome     = cr.cliente.nome     if cr.cliente else "-"
        cliente_cpf_cnpj = cr.cliente.cpf_cnpj if cr.cliente else "-"
        recebidas = sum(1 for p in cr.parcelas if p.recebido)
        total     = len(cr.parcelas)
        valor_recebido = sum(p.valor for p in cr.parcelas if p.recebido)
        valor_aberto   = sum(p.valor for p in cr.parcelas if not p.recebido)
        parcelas_txt = "; ".join(
            f"P{p.numero} vence {p.data_vencimento} R${p.valor:.2f} {'[RECEBIDO]' if p.recebido else '[ABERTO]'}"
            for p in sorted(cr.parcelas, key=lambda x: x.numero)
        )
        classificacoes_txt = ", ".join(
            c.tipo_receita.nome for c in cr.classificacoes if c.tipo_receita
        )
        docs.append(
            f"[CONTA_RECEBER id={cr.id}] "
            f"Emissão:{cr.data_emissao} | Total:R${cr.valor_total:.2f} | "
            f"Recebido:R${valor_recebido:.2f} | Aberto:R${valor_aberto:.2f} | "
            f"Cliente:{cliente_nome}(CPF/CNPJ:{cliente_cpf_cnpj}) | "
            f"Descr:{cr.descricao or '-'} | Class:{classificacoes_txt or '-'} | "
            f"Parcelas({recebidas}/{total} recebidas):[{parcelas_txt}] | "
            f"Status:{'Ativo' if cr.ativo else 'Inativo'}"
        )

    return docs


# ─── Resumo estatístico pré-calculado ─────────────────────────────────────────

def _build_resumo(db: Session) -> str:
    """
    Gera um bloco de RESUMO ESTATÍSTICO pré-calculado diretamente via SQL.
    Esse bloco é sempre incluído no contexto para que o LLM possa responder
    perguntas de totais/contagens sem precisar calcular nada.
    """
    # Contas a Pagar
    cp_all = (
        db.query(models.ContasPagar)
        .options(joinedload(models.ContasPagar.parcelas),
                 joinedload(models.ContasPagar.fornecedor))
        .all()
    )
    cp_total_valor   = sum(c.valor_total for c in cp_all)
    cp_ativos        = [c for c in cp_all if c.ativo]
    cp_inativos      = [c for c in cp_all if not c.ativo]

    # Parcelas a pagar
    todas_parcelas_pagar = [p for c in cp_all for p in c.parcelas]
    pp_pagas   = [p for p in todas_parcelas_pagar if p.pago]
    pp_abertas = [p for p in todas_parcelas_pagar if not p.pago]
    valor_pago_total   = sum(p.valor for p in pp_pagas)
    valor_aberto_total = sum(p.valor for p in pp_abertas)

    # Por fornecedor
    por_fornecedor: Dict[str, float] = defaultdict(float)
    for c in cp_all:
        nome = c.fornecedor.razao_social if c.fornecedor else "Sem fornecedor"
        por_fornecedor[nome] += c.valor_total
    top_forn = sorted(por_fornecedor.items(), key=lambda x: x[1], reverse=True)[:10]

    # Contas a Receber
    cr_all = (
        db.query(models.ContasReceber)
        .options(joinedload(models.ContasReceber.parcelas),
                 joinedload(models.ContasReceber.cliente))
        .all()
    )
    cr_total_valor  = sum(c.valor_total for c in cr_all)
    cr_ativos       = [c for c in cr_all if c.ativo]
    cr_inativos     = [c for c in cr_all if not c.ativo]

    todas_parcelas_receber = [p for c in cr_all for p in c.parcelas]
    pr_recebidas = [p for p in todas_parcelas_receber if p.recebido]
    pr_abertas   = [p for p in todas_parcelas_receber if not p.recebido]
    valor_recebido_total  = sum(p.valor for p in pr_recebidas)
    valor_pendente_total  = sum(p.valor for p in pr_abertas)

    # Por cliente
    por_cliente: Dict[str, float] = defaultdict(float)
    for c in cr_all:
        nome = c.cliente.nome if c.cliente else "Sem cliente"
        por_cliente[nome] += c.valor_total
    top_cli = sorted(por_cliente.items(), key=lambda x: x[1], reverse=True)[:10]

    # Resultado (saldo)
    saldo = cr_total_valor - cp_total_valor

    # Cadastros
    n_fornecedores = db.query(models.Fornecedor).count()
    n_clientes     = db.query(models.Cliente).count()
    n_faturados    = db.query(models.Faturado).count()

    forn_lines = "\n".join(f"  - {n}: R${v:,.2f}" for n, v in top_forn)
    cli_lines  = "\n".join(f"  - {n}: R${v:,.2f}" for n, v in top_cli)

    return f"""=== RESUMO GERAL DO SISTEMA ===

CADASTROS:
  Fornecedores: {n_fornecedores} | Clientes: {n_clientes} | Faturados: {n_faturados}

CONTAS A PAGAR:
  Total de contas: {len(cp_all)} (Ativas: {len(cp_ativos)} | Inativas: {len(cp_inativos)})
  Valor total das contas: R${cp_total_valor:,.2f}
  Total de parcelas: {len(todas_parcelas_pagar)} (Pagas: {len(pp_pagas)} | Abertas: {len(pp_abertas)})
  Valor já pago: R${valor_pago_total:,.2f}
  Valor em aberto (a pagar): R${valor_aberto_total:,.2f}
  Top fornecedores por valor:
{forn_lines}

CONTAS A RECEBER:
  Total de contas: {len(cr_all)} (Ativas: {len(cr_ativos)} | Inativas: {len(cr_inativos)})
  Valor total das contas: R${cr_total_valor:,.2f}
  Total de parcelas: {len(todas_parcelas_receber)} (Recebidas: {len(pr_recebidas)} | Abertas: {len(pr_abertas)})
  Valor já recebido: R${valor_recebido_total:,.2f}
  Valor pendente (a receber): R${valor_pendente_total:,.2f}
  Top clientes por valor:
{cli_lines}

RESULTADO (SALDO):
  Total a receber - Total a pagar = R${saldo:,.2f} {'(POSITIVO)' if saldo >= 0 else '(NEGATIVO)'}
"""


# ─── LLM ──────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Você é um assistente financeiro direto e preciso, especializado em notas fiscais, contas a pagar e receber.

REGRAS OBRIGATÓRIAS:
1. Responda SEMPRE em português brasileiro.
2. Seja DIRETO: vá ao ponto, mostre os números logo na primeira linha da resposta.
3. Use tabelas ou listas com valores numéricos quando a pergunta envolver valores, datas ou contagens.
4. NUNCA diga "preciso de mais informações" — você JÁ TEM todos os dados disponíveis abaixo.
5. NUNCA diga "não tenho acesso" — use os dados fornecidos.
6. Se um registro não existir, diga exatamente: "Não encontrado nos dados do sistema."
7. Mostre valores monetários sempre no formato R$ X.XXX,XX (reais com separador de milhar).
8. Em respostas sobre totais ou resumos, inclua sempre: quantidade de registros, valor total, valor pago/recebido e valor em aberto.
9. NUNCA invente dados. Use exclusivamente o que está nos blocos abaixo.\
"""


def _call_llm(
    client: ollama.Client,
    model: str,
    pergunta: str,
    resumo: str,
    docs_relevantes: List[str],
) -> str:
    n_docs = len(docs_relevantes)
    docs_txt = "\n".join(docs_relevantes)

    user_msg = (
        f"{resumo}\n"
        f"=== REGISTROS MAIS RELEVANTES PARA ESTA PERGUNTA ({n_docs} selecionados) ===\n"
        f"{docs_txt}\n\n"
        f"=== PERGUNTA ===\n{pergunta}\n\n"
        f"Responda de forma direta e completa usando os dados acima. "
        f"Mostre números, valores e datas exatos dos registros."
    )

    try:
        resp = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            options={"temperature": 0.05, "num_predict": 512, "num_ctx": 4096},
        )
        return resp.message.content.strip()
    except ollama.ResponseError as e:
        err = str(e).lower()
        if "not found" in err or "pull" in err:
            raise HTTPException(
                503,
                f"Modelo '{model}' não encontrado. "
                f"Execute: docker compose exec ollama ollama pull {model}",
            )
        raise HTTPException(502, f"Ollama ResponseError: {e}")
    except Exception as e:
        raise HTTPException(502, f"Erro ao chamar o LLM: {type(e).__name__}: {e}")


# ─── Embeddings ───────────────────────────────────────────────────────────────

def _embed_texts(client: ollama.Client, model: str, texts: List[str]) -> np.ndarray:
    try:
        resp = client.embed(model=model, input=texts)
        return np.array(resp.embeddings, dtype=np.float32)
    except ollama.ResponseError as e:
        err = str(e).lower()
        if "not found" in err or "pull" in err:
            raise HTTPException(
                503,
                f"Modelo de embedding '{model}' não encontrado. "
                f"Execute: docker compose exec ollama ollama pull {model}",
            )
        raise HTTPException(502, f"Ollama embed error: {e}")
    except Exception as e:
        raise HTTPException(502, f"Erro ao gerar embeddings: {type(e).__name__}: {e}")


def _cosine_similarity(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    q = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    d = doc_vecs  / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-10)
    return d @ q


def _get_or_build_index(
    client: ollama.Client,
    embed_model: str,
    documentos: List[str],
) -> Tuple[np.ndarray, bool]:
    current_hash = _docs_hash(documentos)
    if _cache.is_valid(current_hash):
        print(f"[RAG:cache] ✔ Cache hit — {len(documentos)} docs indexados.")
        return _cache.vectors, True  # type: ignore[return-value]

    print(f"[RAG:cache] ✘ Cache miss — indexando {len(documentos)} docs...")
    vectors = _embed_texts(client, embed_model, documentos)
    _cache.update(documentos, vectors, current_hash)
    return vectors, False


def _get_query_embedding(
    client: ollama.Client,
    embed_model: str,
    pergunta: str,
) -> Tuple[np.ndarray, bool]:
    cached = _cache.get_query_vec(pergunta)
    if cached is not None:
        print(f"[RAG:cache] ✔ Query cache hit: '{pergunta[:50]}'")
        return cached, True
    vec = _embed_texts(client, embed_model, [pergunta])[0]
    _cache.set_query_vec(pergunta, vec)
    return vec, False


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/embeddings", response_model=RagResponse)
def rag_embeddings(body: RagRequest, db: Session = Depends(get_db)):
    """
    RAG principal: busca semântica + resumo estatístico pré-calculado.

    Contexto enviado ao LLM:
      1. Resumo geral (totais, saldos, top fornecedores/clientes) — pré-calculado no Python
      2. Top-K documentos mais relevantes para a pergunta — via similarity coseno
    """
    t0     = time.perf_counter()
    cfg    = _cfg()
    client = _get_ollama_client()
    top_k  = min(max(1, body.top_k), _MAX_TOP_K)

    # 1. Documentos do banco
    documentos = _build_documents(db)
    if not documentos:
        raise HTTPException(404, "Nenhum dado encontrado no banco de dados.")

    # 2. Resumo estatístico pré-calculado (sempre incluído)
    resumo = _build_resumo(db)

    try:
        # 3. Índice vetorial (cache)
        doc_vecs, index_hit = _get_or_build_index(client, cfg["embed_model"], documentos)

        # 4. Embedding da query (cache)
        query_vec, query_hit = _get_query_embedding(client, cfg["embed_model"], body.pergunta)

        # 5. Seleciona top-K mais relevantes
        scores      = _cosine_similarity(query_vec, doc_vecs)
        k           = min(top_k, len(documentos))
        top_indices = np.argsort(scores)[::-1][:k]

        # Truncação adaptativa
        max_chars = max(300, _MAX_DOC_CHARS - (k // 10) * 30)
        docs_selecionados = [
            d[:max_chars] + ("…" if len(d) > max_chars else "")
            for d in (documentos[i] for i in top_indices)
        ]

        # 6. Chama o LLM com resumo + docs
        resposta = _call_llm(client, cfg["llm_model"], body.pergunta, resumo, docs_selecionados)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Erro no RAG: {type(e).__name__}: {e}")

    tempo_ms  = (time.perf_counter() - t0) * 1000
    cache_hit = index_hit and query_hit

    return RagResponse(
        resposta=resposta,
        modo="embeddings",
        documentos_usados=len(docs_selecionados),
        total_documentos=len(documentos),
        cache_hit=cache_hit,
        tempo_ms=round(tempo_ms, 1),
    )


@router.post("/simples", response_model=RagResponse)
def rag_simples(body: RagRequest, db: Session = Depends(get_db)):
    """RAG simples: resumo estatístico + amostra de docs sem busca semântica."""
    t0     = time.perf_counter()
    cfg    = _cfg()
    client = _get_ollama_client()
    top_k  = min(max(1, body.top_k), _MAX_TOP_K)

    documentos = _build_documents(db)
    if not documentos:
        raise HTTPException(404, "Nenhum dado encontrado no banco de dados.")

    resumo = _build_resumo(db)
    docs_usados = [
        d[:_MAX_DOC_CHARS] + ("…" if len(d) > _MAX_DOC_CHARS else "")
        for d in documentos[:top_k]
    ]

    try:
        resposta = _call_llm(client, cfg["llm_model"], body.pergunta, resumo, docs_usados)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Erro ao chamar o modelo: {type(e).__name__}: {e}")

    tempo_ms = (time.perf_counter() - t0) * 1000
    return RagResponse(
        resposta=resposta,
        modo="simples",
        documentos_usados=len(docs_usados),
        total_documentos=len(documentos),
        cache_hit=False,
        tempo_ms=round(tempo_ms, 1),
    )


@router.get("/cache/status", summary="Status do cache de embeddings")
def cache_status():
    built = _cache.built_at
    return {
        "indexado": _cache.vectors is not None,
        "total_documentos": len(_cache.documentos),
        "queries_em_cache": len(_cache._query_cache),
        "hash": _cache.docs_hash[:16] + "..." if _cache.docs_hash else None,
        "criado_em": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(built)) if built else None,
    }


@router.delete("/cache", summary="Invalida o cache de embeddings")
def invalidar_cache():
    _cache.invalidate()
    return {"mensagem": "Cache de embeddings invalidado com sucesso."}
