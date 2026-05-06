# NF Extractor

Interface web para **upload de nota fiscal em PDF**, extração de dados via **LLM (Gemini)** e lançamento automático em **Contas a Pagar**.

## Como rodar

### Opção 1 — Docker Compose (recomendado)

Sobe PostgreSQL + API + Frontend de uma vez:

```bash
copy api\.env.example api\.env
# edite api\.env e preencha GEMINI_API_KEY
docker compose up --build
```

Acesse `http://localhost:5173`.

### Opção 2 — Local (sem Docker)

**Backend:**

```bash
cd api
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edite .env e preencha GEMINI_API_KEY e DATABASE_URL
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

**Frontend** (em outro terminal):

```bash
cd app
npm install
npm run dev
```

Acesse `http://localhost:5173`.

## Variáveis de ambiente (`api/.env`)

| Variável | Descrição | Padrão |
|---|---|---|
| `GEMINI_API_KEY` | Chave da API do Google Gemini | — |
| `GEMINI_MODEL` | Modelo Gemini a usar | `gemini-2.5-flash` |
| `ALLOWED_ORIGINS` | Origins permitidas no CORS | `http://localhost:5173` |
| `DATABASE_URL` | Connection string do PostgreSQL | `postgresql://postgres:postgres@localhost:5432/nfextractor` |

> Se o Gemini retornar erro `503 UNAVAILABLE`, aguarde alguns minutos (pico de demanda) ou troque `GEMINI_MODEL` para `gemini-1.5-flash`.

## Funcionalidades

- Upload de PDF via drag-and-drop ou clique
- Extração de dados da NF via Gemini (fornecedor, faturado, parcelas, classificações de despesa)
- Painel de análise: verifica quais registros já existem no banco antes de lançar
- Lançamento automático em Contas a Pagar (cria fornecedor, faturado e tipos de despesa se não existirem)
- CRUDs completos: Fornecedores, Clientes, Faturados, Tipos de Despesa, Tipos de Receita, Contas a Pagar, Contas a Receber

