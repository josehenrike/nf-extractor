import json
import os
from io import BytesIO
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from pypdf import PdfReader

load_dotenv(override=True)

import models  # noqa: E402
from database import engine, get_db  # noqa: E402
from routers import fornecedores, clientes, faturados, tipos_despesa, tipos_receita, contas_pagar, contas_receber, nf_lancar  # noqa: E402

# cria tabelas automaticamente se não existirem
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NF Extractor - Sistema Administrativo-Financeiro")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers CRUD 
app.include_router(fornecedores.router)
app.include_router(clientes.router)
app.include_router(faturados.router)
app.include_router(tipos_despesa.router)
app.include_router(tipos_receita.router)
app.include_router(contas_pagar.router)
app.include_router(contas_receber.router)
app.include_router(nf_lancar.router)


# Health 

@app.get("/health", tags=["Sistema"])
def health():
    load_dotenv(override=True)
    return {"ok": True, "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")}


# Extração de NF (Etapa 1) 

class _Fornecedor(BaseModel):
    razao_social: str = Field(..., description="Razão social")
    fantasia: Optional[str] = Field(None)
    cnpj: str

class _Faturado(BaseModel):
    nome_completo: str
    cpf: str

class _Parcela(BaseModel):
    data_vencimento: str
    valor: Optional[float] = None

class ExtracaoNf(BaseModel):
    fornecedor: _Fornecedor
    faturado: _Faturado
    numero_nota_fiscal: str
    data_emissao: str
    descricao_produtos: str
    quantidade_parcelas: int = Field(..., ge=1)
    parcelas: List[_Parcela]
    valor_total: float
    classificacoes_despesa: List[str]


def _env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if not value or not value.strip():
        raise RuntimeError(f"Variável de ambiente ausente: {name}")
    return value


def _parse_json(text: str) -> Dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        lines = t.splitlines()
        if lines and lines[0].lower().startswith("json"):
            lines = lines[1:]
        t = "\n".join(lines).strip()
    try:
        return json.loads(t)
    except Exception:
        start, end = t.find("{"), t.rfind("}")
        if start != -1 and end > start:
            return json.loads(t[start:end + 1])
        raise


def _pdf_to_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(line.rstrip() for line in "\n".join(parts).splitlines()).strip()


@app.post("/extract", response_model=ExtracaoNf, tags=["Extração NF"])
async def extract(file: UploadFile = File(...)):
    load_dotenv(override=True)
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, "Envie um arquivo PDF.")

    try:
        api_key = _env("GEMINI_API_KEY")
        model   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(400, "Arquivo vazio.")

    nf_text = _pdf_to_text(pdf_bytes)
    if not nf_text:
        raise HTTPException(400, "Não foi possível extrair texto do PDF (imagem/scaneado).")

    prompt = """
Você é um extrator de dados de NOTA FISCAL para CONTAS A PAGAR.
Responda com JSON VÁLIDO (sem markdown) com esta estrutura:
{
  "fornecedor": {"razao_social": "...", "fantasia": "...", "cnpj": "..."},
  "faturado": {"nome_completo": "...", "cpf": "..."},
  "numero_nota_fiscal": "...",
  "data_emissao": "YYYY-MM-DD",
  "descricao_produtos": "...",
  "quantidade_parcelas": 1,
  "parcelas": [{"data_vencimento": "YYYY-MM-DD", "valor": 0.0}],
  "valor_total": 0.0,
  "classificacoes_despesa": ["..."]
}
Regras:
- Campos ausentes: string vazia ou null.
- Datas em YYYY-MM-DD.
- Valores numéricos com ponto decimal.
- classificacoes_despesa inferida pelos produtos/serviços. Categorias: INSUMOS AGRÍCOLAS, MANUTENÇÃO E OPERAÇÃO, RECURSOS HUMANOS, SERVIÇOS OPERACIONAIS, INFRAESTRUTURA E UTILIDADES, ADMINISTRATIVAS, SEGUROS E PROTEÇÃO, IMPOSTOS E TAXAS, INVESTIMENTOS.
""".strip()

    try:
        resp = genai.Client(api_key=api_key).models.generate_content(
            model=model,
            contents=[prompt, f"TEXTO DA NOTA FISCAL:\n{nf_text}"],
            config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json"),
        )
        text = (resp.text or "").strip()
        if not text:
            raise HTTPException(502, "Modelo não retornou conteúdo.")
        return ExtracaoNf.model_validate(_parse_json(text))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Falha ao extrair via Gemini: {type(e).__name__}: {e}")
