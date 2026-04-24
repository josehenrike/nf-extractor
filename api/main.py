import json
import os
from io import BytesIO
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pypdf import PdfReader


load_dotenv(override=True)


class Fornecedor(BaseModel):
    razao_social: str = Field(..., description="Razão social do fornecedor")
    fantasia: Optional[str] = Field(None, description="Nome fantasia do fornecedor")
    cnpj: str = Field(..., description="CNPJ do fornecedor")


class Faturado(BaseModel):
    nome_completo: str = Field(..., description="Nome completo do faturado")
    cpf: str = Field(..., description="CPF do faturado")


class Parcela(BaseModel):
    data_vencimento: str = Field(..., description="Data de vencimento (YYYY-MM-DD, se possível)")
    valor: Optional[float] = Field(None, description="Valor da parcela (se disponível)")


class ExtracaoNf(BaseModel):
    fornecedor: Fornecedor
    faturado: Faturado
    numero_nota_fiscal: str
    data_emissao: str
    descricao_produtos: str
    quantidade_parcelas: int = Field(..., ge=1)
    parcelas: List[Parcela]
    valor_total: float
    classificacoes_despesa: List[str] = Field(
        ..., description="Uma ou mais categorias de despesa interpretadas a partir dos itens"
    )


def _env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Variável de ambiente ausente: {name}")
    return value


def _parse_json_response(text: str) -> Dict[str, Any]:
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
        start = t.find("{")
        end = t.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(t[start : end + 1])
        raise


def _pdf_to_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    parts: List[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    text = "\n".join(parts)
    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    return text


app = FastAPI(title="NF Extractor - Etapa 1")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    load_dotenv(override=True)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return {"ok": True, "model": model}


@app.post("/extract", response_model=ExtracaoNf)
async def extract(file: UploadFile = File(...)):
    load_dotenv(override=True)
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF.")

    try:
        api_key = _env("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    client = genai.Client(api_key=api_key)

    nf_text = _pdf_to_text(pdf_bytes)
    if not nf_text:
        raise HTTPException(
            status_code=400,
            detail="Não consegui extrair texto do PDF (parece ser imagem/scaneado). Use um PDF com texto ou aplique OCR antes.",
        )

    prompt = f"""
Você é um extrator de dados de NOTA FISCAL para CONTAS A PAGAR.

Você receberá o TEXTO da nota fiscal. Responda com JSON VÁLIDO (sem markdown, sem texto extra) com esta estrutura:

{{
  "fornecedor": {{"razao_social": "...", "fantasia": "...", "cnpj": "..."}},
  "faturado": {{"nome_completo": "...", "cpf": "..."}},
  "numero_nota_fiscal": "...",
  "data_emissao": "...",
  "descricao_produtos": "...",
  "quantidade_parcelas": 1,
  "parcelas": [{{"data_vencimento": "...", "valor": null}}],
  "valor_total": 0.0,
  "classificacoes_despesa": ["..."]
}}

Regras:
- Se algum campo não estiver claramente no PDF, preencha com string vazia ("") ou null quando fizer sentido, mas mantenha a estrutura.
- datas: prefira YYYY-MM-DD (se não conseguir, mantenha como aparece no documento).
- valor_total e valor (parcela) devem ser números (use ponto como separador decimal).
- quantidade_parcelas: por enquanto use 1, mas mantenha lista parcelas com 1 item.
- classificacoes_despesa: deve ser uma lista com 1 ou mais categorias principais (ex.: "MANUTENÇÃO E OPERAÇÃO", "INFRAESTRUTURA E UTILIDADES", "INSUMOS AGRÍCOLAS", "RECURSOS HUMANOS", "SERVIÇOS OPERACIONAIS", "ADMINISTRATIVAS", "SEGUROS E PROTEÇÃO", "IMPOSTOS E TAXAS", "INVESTIMENTOS").
- A classificação de despesa NÃO é um campo extraído literalmente; deve ser inferida pela descrição dos produtos/serviços.
""".strip()

    try:
        contents = [prompt, f"TEXTO DA NOTA FISCAL:\n{nf_text}"]
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )

        text = (resp.text or "").strip()
        if not text:
            raise HTTPException(status_code=502, detail="Modelo não retornou conteúdo.")

        data = _parse_json_response(text)
        return ExtracaoNf.model_validate(data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao extrair dados via Gemini: {type(e).__name__}: {e}",
        )

