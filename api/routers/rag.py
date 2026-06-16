from __future__ import annotations

import hashlib
import json
import os
import time
import unicodedata
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from groq import Groq
from rank_bm25 import BM25Okapi

from database import get_db
import models

router = APIRouter(prefix="/rag", tags=["RAG – Consulta Inteligente"])

class RagRequest(BaseModel):
    pergunta: str
    top_k: int = 25

class RagResponse(BaseModel):
    resposta: str
    modo: str
    documentos_usados: int
    total_documentos: int
    cache_hit: bool = False
    tempo_ms: float = 0.0
    sql_query: Optional[str] = None

def _cfg() -> dict:
    load_dotenv(override=False)
    return {
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "llm_model":    os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    }

_MAX_DOC_CHARS = 1000
_MAX_TOP_K     = 25

SQL_GENERATION_PROMPT = """Você é um tradutor de perguntas em linguagem natural para consultas SQL do PostgreSQL.
O banco de dados possui o seguinte esquema:

Tabelas de Cadastros:
1. `fornecedores` (id: SERIAL PRIMARY KEY, razao_social: VARCHAR(200) NOT NULL, fantasia: VARCHAR(200), cnpj: VARCHAR(20) UNIQUE NOT NULL, ativo: BOOLEAN NOT NULL DEFAULT TRUE)
2. `clientes` (id: SERIAL PRIMARY KEY, nome: VARCHAR(200) NOT NULL, cpf_cnpj: VARCHAR(20) UNIQUE NOT NULL, email: VARCHAR(200), telefone: VARCHAR(30), ativo: BOOLEAN NOT NULL DEFAULT TRUE)
3. `faturados` (id: SERIAL PRIMARY KEY, nome_completo: VARCHAR(200) NOT NULL, cpf: VARCHAR(20) UNIQUE NOT NULL, ativo: BOOLEAN NOT NULL DEFAULT TRUE)
4. `tipos_despesa` (id: SERIAL PRIMARY KEY, nome: VARCHAR(100) UNIQUE NOT NULL, descricao: VARCHAR(300), ativo: BOOLEAN NOT NULL DEFAULT TRUE)
5. `tipos_receita` (id: SERIAL PRIMARY KEY, nome: VARCHAR(100) UNIQUE NOT NULL, descricao: VARCHAR(300), ativo: BOOLEAN NOT NULL DEFAULT TRUE)

Tabelas de Contas a Pagar:
6. `contas_pagar` (id: SERIAL PRIMARY KEY, numero_nf: VARCHAR(50), data_emissao: DATE NOT NULL, descricao: TEXT, valor_total: DOUBLE PRECISION NOT NULL, fornecedor_id: INTEGER REFERENCES fornecedores(id), faturado_id: INTEGER REFERENCES faturados(id), ativo: BOOLEAN NOT NULL DEFAULT TRUE)
7. `parcelas_pagar` (id: SERIAL PRIMARY KEY, conta_id: INTEGER REFERENCES contas_pagar(id), numero: INTEGER NOT NULL DEFAULT 1, data_vencimento: DATE NOT NULL, valor: DOUBLE PRECISION NOT NULL, pago: BOOLEAN NOT NULL DEFAULT FALSE)
8. `classificacoes_pagar` (id: SERIAL PRIMARY KEY, conta_id: INTEGER REFERENCES contas_pagar(id), tipo_despesa_id: INTEGER REFERENCES tipos_despesa(id))

Tabelas de Contas a Receber:
9. `contas_receber` (id: SERIAL PRIMARY KEY, descricao: TEXT, data_emissao: DATE NOT NULL, valor_total: DOUBLE PRECISION NOT NULL, cliente_id: INTEGER REFERENCES clientes(id), ativo: BOOLEAN NOT NULL DEFAULT TRUE)
10. `parcelas_receber` (id: SERIAL PRIMARY KEY, conta_id: INTEGER REFERENCES contas_receber(id), numero: INTEGER NOT NULL DEFAULT 1, data_vencimento: DATE NOT NULL, valor: DOUBLE PRECISION NOT NULL, recebido: BOOLEAN NOT NULL DEFAULT FALSE)
11. `classificacoes_receber` (id: SERIAL PRIMARY KEY, conta_id: INTEGER REFERENCES contas_receber(id), tipo_receita_id: INTEGER REFERENCES tipos_receita(id))

Regras Importantes:
1. Retorne APENAS a query SQL válida do PostgreSQL, sem qualquer formatação em markdown (sem ```sql ou ```), sem explicações, sem comentários.
2. A consulta deve ser estritamente de leitura (SELECT). Não use INSERT, UPDATE, DELETE, DROP, etc.
3. Se a pergunta for sobre "este mês", "mês passado", "este ano", etc., baseie-se na data atual de hoje: {current_date}.
4. Lide com associações de tabelas (JOINs) corretamente:
   - ATENÇÃO: O campo `pago` (indica se a parcela está paga/em aberto) fica na tabela `parcelas_pagar`, e NÃO em `contas_pagar`. Para filtrar por contas/parcelas a pagar em aberto ou pagas, você DEVE fazer JOIN com `parcelas_pagar` e filtrar por `parcelas_pagar.pago = FALSE` (em aberto) ou `parcelas_pagar.pago = TRUE` (pagas).
   - ATENÇÃO: O campo `recebido` (indica se a parcela está recebida/em aberto) fica na tabela `parcelas_receber`, e NÃO em `contas_receber`. Para filtrar por contas/parcelas a receber em aberto ou recebidas, você DEVE fazer JOIN com `parcelas_receber` e filtrar por `parcelas_receber.recebido = FALSE` (em aberto) ou `parcelas_receber.recebido = TRUE` (recebidas).
   - Relacione `contas_pagar` com `fornecedores` através de `contas_pagar.fornecedor_id = fornecedores.id`.
   - Relacione `contas_receber` com `clientes` através de `contas_receber.cliente_id = clientes.id`.
   - Para filtrar por tipo de despesa, faça JOIN entre `contas_pagar`, `classificacoes_pagar` (no campo `conta_id`) e `tipos_despesa` (no campo `tipo_despesa_id`).
   - Para filtrar por tipo de receita, faça JOIN entre `contas_receber`, `classificacoes_receber` (no campo `conta_id`) e `tipos_receita` (no campo `tipo_receita_id`).
5. Sempre verifique se o campo `ativo` é TRUE nas tabelas principais (`contas_pagar`, `contas_receber`, `fornecedores`, `clientes`, `faturados`) para trazer apenas registros válidos, a menos que a pergunta peça especificamente por inativos.
"""

FINAL_RESPONSE_PROMPT = """Você é um assistente financeiro inteligente integrado com acesso de leitura ao banco de dados PostgreSQL do sistema NF Extractor.

O usuário fez a seguinte pergunta: "{pergunta}"

Consulta SQL gerada e executada internamente (NÃO mencione ou mostre esta consulta na resposta):
```sql
{sql}
```

O resultado retornado pelo banco de dados foi:
{results_json}

Com base EXCLUSIVAMENTE nesses dados, responda à pergunta do usuário de forma clara, objetiva e em português do Brasil.
Diretrizes:
1. Responda diretamente à pergunta. Use dados e números exatos do resultado.
2. Apresente os dados estruturados de forma legível (se aplicável, use listas ou tabelas simuladas em markdown simples).
3. Se nenhum dado for retornado, informe que não há registros correspondentes no banco de dados.
4. IMPORTANTE: Nunca mostre, mencione ou faça referência à consulta SQL executada, às tabelas/colunas consultadas ou a detalhes técnicos do banco de dados na sua resposta. Responda apenas de forma direta e clara sobre os dados financeiros reais retornados.
"""

def _generate_sql(pergunta: str) -> str:
    cfg = _cfg()
    client = Groq(api_key=cfg["groq_api_key"])
    current_date = date.today().isoformat()
    system_prompt = SQL_GENERATION_PROMPT.format(current_date=current_date)
    
    try:
        completion = client.chat.completions.create(
            model=cfg["llm_model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Pergunta: {pergunta}"}
            ],
            max_tokens=600,
            temperature=0.0
        )
        sql = completion.choices[0].message.content.strip()
        # Clean up code blocks if the LLM output wrapped it
        if sql.startswith("```"):
            lines = sql.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            sql = "\n".join(lines).strip()
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()
        return sql
    except Exception as e:
        raise HTTPException(502, f"Erro ao gerar SQL com LLM: {e}")

def _execute_sql(db: Session, sql: str) -> Tuple[List[dict], List[str], Optional[str]]:
    try:
        # Check read-only
        sql_clean = sql.strip().lower()
        if not sql_clean.startswith("select"):
            return [], [], "Apenas consultas SELECT (leitura) são permitidas por segurança."
            
        result = db.execute(text(sql))
        columns = list(result.keys())
        rows = []
        for row in result.fetchall():
            row_dict = {}
            for col, val in zip(columns, row):
                if isinstance(val, date):
                    row_dict[col] = val.isoformat()
                else:
                    row_dict[col] = val
            rows.append(row_dict)
        return rows, columns, None
    except SQLAlchemyError as e:
        return [], [], str(e)

def _clean(text: str) -> str:
    if not text:
        return "-"
    # Normaliza e remove acentos para economizar tokens no Groq
    cleaned = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return cleaned.strip()

def _build_documents(db: Session, pergunta: str) -> List[str]:
    pergunta_lower = pergunta.lower()
    
    # Detecção se a pergunta é focada em receitas ou despesas
    is_receita = any(k in pergunta_lower for k in ['receber', 'receita', 'faturamento', 'cliente', 'venda', 'recebi', 'entrada'])
    is_despesa = any(k in pergunta_lower for k in ['pagar', 'despesa', 'compra', 'fornecedor', 'paguei', 'saída', 'manutenção', 'insumo', 'recursos humanos', 'serviços operacionais', 'infraestrutura', 'administrativas', 'seguro', 'imposto', 'investimento', 'combustível', 'peças', 'salário', 'colheita', 'energia', 'frete', 'aluguel', 'semente'])
    
    include_pagar = True
    include_receber = True
    if is_receita and not is_despesa:
        include_pagar = False
    elif is_despesa and not is_receita:
        include_receber = False

    docs: List[str] = []
    
    if include_pagar:
        contas_pagar = db.query(models.ContasPagar).options(
            joinedload(models.ContasPagar.parcelas),
            joinedload(models.ContasPagar.classificacoes).joinedload(models.ClassificacaoPagar.tipo_despesa),
            joinedload(models.ContasPagar.fornecedor)
        ).all()
        for cp in contas_pagar:
            forn_nome = _clean(cp.fornecedor.razao_social[:20]) if cp.fornecedor else "-"
            num_nf = cp.numero_nf or "-"
            pagas = sum(1 for p in cp.parcelas if p.pago)
            abertas = len(cp.parcelas) - pagas
            cats = ",".join(_clean(c.tipo_despesa.nome[:15]) for c in cp.classificacoes if c.tipo_despesa)
            desc = _clean(cp.descricao)
            if " - Ref." in desc:
                desc = desc.split(" - Ref.")[0]
            if " — Ref." in desc:
                desc = desc.split(" — Ref.")[0]
            desc = desc[:30].strip()
            dt_str = cp.data_emissao.strftime("%y-%m-%d") if cp.data_emissao else "-"
            # CP[id]|[Número da Nota]|[Fornecedor]|[Valor Total]|[Parcelas Pagas]p/[Parcelas Abertas]a|[Categorias Despesa]|[Descrição]|[Data de Emissão YY-MM-DD]
            docs.append(f"CP{cp.id}|{num_nf}|{forn_nome}|{cp.valor_total:.2f}|{pagas}p/{abertas}a|{cats}|{desc}|{dt_str}")

    if include_receber:
        contas_receber = db.query(models.ContasReceber).options(
            joinedload(models.ContasReceber.parcelas),
            joinedload(models.ContasReceber.classificacoes).joinedload(models.ClassificacaoReceber.tipo_receita),
            joinedload(models.ContasReceber.cliente)
        ).all()
        for cr in contas_receber:
            cli_nome = _clean(cr.cliente.nome[:20]) if cr.cliente else "-"
            num_nf = "-"
            recebidas = sum(1 for p in cr.parcelas if p.recebido)
            abertas = len(cr.parcelas) - recebidas
            cats = ",".join(_clean(c.tipo_receita.nome[:15]) for c in cr.classificacoes if c.tipo_receita)
            desc = _clean(cr.descricao)
            if " - Ref." in desc:
                desc = desc.split(" - Ref.")[0]
            if " — Ref." in desc:
                desc = desc.split(" — Ref.")[0]
            desc = desc[:30].strip()
            dt_str = cr.data_emissao.strftime("%y-%m-%d") if cr.data_emissao else "-"
            # CR[id]|[Número da Nota]|[Cliente]|[Valor Total]|[Parcelas Recebidas]r/[Parcelas Abertas]a|[Categorias Receita]|[Descrição]|[Data de Emissão YY-MM-DD]
            docs.append(f"CR{cr.id}|{num_nf}|{cli_nome}|{cr.valor_total:.2f}|{recebidas}r/{abertas}a|{cats}|{desc}|{dt_str}")

    return docs

def _build_resumo(db: Session) -> str:
    cp_all = db.query(models.ContasPagar).options(joinedload(models.ContasPagar.parcelas), joinedload(models.ContasPagar.fornecedor)).all()
    cr_all = db.query(models.ContasReceber).options(joinedload(models.ContasReceber.parcelas), joinedload(models.ContasReceber.cliente)).all()
    cp_total = sum(c.valor_total for c in cp_all)
    cr_total = sum(c.valor_total for c in cr_all)
    return f"RESUMO: {len(cp_all)} contas a pagar (R${cp_total:.2f}). {len(cr_all)} contas a receber (R${cr_total:.2f})."

_SYSTEM_PROMPT = """Você é um assistente financeiro. Responda a pergunta com base nos DADOS RELEVANTES do banco de dados fornecidos abaixo.
Os dados das contas estão no formato compacto sem acentos para economizar espaço de tokens:
Formato das Contas a Pagar: CP[id]|[Número da Nota]|[Fornecedor]|[Valor Total]|[Parcelas Pagas]p/[Parcelas Abertas]a|[Categorias Despesa]|[Descrição]|[Data de Emissão YY-MM-DD]
Formato das Contas a Receber: CR[id]|[Número da Nota]|[Cliente]|[Valor Total]|[Parcelas Recebidas]r/[Parcelas Abertas]a|[Categorias Receita]|[Descrição]|[Data de Emissão YY-MM-DD]
Sempre forneça os detalhes reais das contas nas respostas de forma amigável e legível, mencionando os nomes dos fornecedores, categorias, valores e o número exato da nota fiscal (NF) quando for listá-los.
Seja exato nas respostas e use os dados fornecidos. Nunca mencione termos técnicos de banco de dados, queries SQL ou estrutura interna de tabelas."""

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
    documentos = _build_documents(db, body.pergunta)
    if not documentos:
        raise HTTPException(404, "Nenhum dado.")
    
    resposta = _call_llm(_cfg()["llm_model"], body.pergunta, _build_resumo(db), documentos)
    
    return RagResponse(
        resposta=resposta,
        modo="embeddings",
        documentos_usados=len(documentos),
        total_documentos=len(documentos),
        tempo_ms=round((time.perf_counter() - t0)*1000, 1),
    )

@router.post("/simples", response_model=RagResponse)
def rag_simples(body: RagRequest, db: Session = Depends(get_db)):
    t0 = time.perf_counter()
    pergunta = body.pergunta
    
    # 1. Gerar query SQL
    sql = _generate_sql(pergunta)
    
    # 2. Executar no banco
    rows, columns, error = _execute_sql(db, sql)
    
    if error:
        print(f"Erro na execução da query gerada: {error}\nQuery: {sql}")
        resposta_erro = "Desculpe, ocorreu um erro ao buscar os dados no banco de dados. Por favor, tente reformular a pergunta."
        return RagResponse(
            resposta=resposta_erro,
            modo="simples",
            documentos_usados=0,
            total_documentos=0,
            tempo_ms=round((time.perf_counter() - t0)*1000, 1),
            sql_query=None
        )
        
    # 3. Formular resposta com LLM
    cfg = _cfg()
    client = Groq(api_key=cfg["groq_api_key"])
    
    try:
        results_json = json.dumps(rows, indent=2, ensure_ascii=False)
        system_prompt = FINAL_RESPONSE_PROMPT.format(
            pergunta=pergunta,
            sql=sql,
            results_json=results_json
        )
        
        completion = client.chat.completions.create(
            model=cfg["llm_model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Gere a resposta final baseada estritamente nos dados acima."}
            ],
            max_tokens=1500,
        )
        resposta = completion.choices[0].message.content.strip()
    except Exception as e:
        resposta = f"Erro ao formular resposta: {e}\n\n**Dados brutos retornados pelo banco:**\n{rows}"

    return RagResponse(
        resposta=resposta,
        modo="simples",
        documentos_usados=len(rows),
        total_documentos=11,
        tempo_ms=round((time.perf_counter() - t0)*1000, 1),
        sql_query=sql
    )
