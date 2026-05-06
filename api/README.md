# API (Python)

## Requisitos

- Python 3.10+ (recomendado 3.12)
- PostgreSQL 14+

## Configuração

Crie um `.env` baseado em `.env.example`:

- `GEMINI_API_KEY` — obrigatório
- `GEMINI_MODEL` — padrão `gemini-2.5-flash`
- `ALLOWED_ORIGINS` — padrão `http://localhost:5173`
- `DATABASE_URL` — connection string do PostgreSQL

## Rodar local

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

## Principais endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Status da API |
| `POST` | `/extract` | Extrai dados de PDF via Gemini |
| `POST` | `/nf/analisar` | Verifica registros existentes no banco |
| `POST` | `/nf/lancar` | Lança NF como Conta a Pagar |
| `GET/POST/PUT` | `/fornecedores` | CRUD de fornecedores |
| `GET/POST/PUT` | `/clientes` | CRUD de clientes |
| `GET/POST/PUT` | `/faturados` | CRUD de faturados |
| `GET/POST/PUT` | `/tipos-despesa` | CRUD de tipos de despesa |
| `GET/POST/PUT` | `/tipos-receita` | CRUD de tipos de receita |
| `GET/POST/PUT` | `/contas-pagar` | CRUD de contas a pagar |
| `GET/POST/PUT` | `/contas-receber` | CRUD de contas a receber |

Documentação interativa: `http://localhost:8001/docs`

