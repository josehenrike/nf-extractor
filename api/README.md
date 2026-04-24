# API (Python / FastAPI)

## Requisitos

- Python 3.10+ (recomendado 3.11+)

## Configuração

Crie um `.env` (ou exporte variáveis) baseado em `.env.example`:

- `GEMINI_API_KEY`
- `GEMINI_MODEL` (opcional)
- `ALLOWED_ORIGINS` (opcional)

## Rodar local

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Saúde:

- `GET http://localhost:8000/health`

Extração:

- `POST http://localhost:8000/extract` (multipart com campo `file` PDF)

