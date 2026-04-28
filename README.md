# NF Extractor 

Este projeto implementa a **Etapa 1** do enunciado: uma interface web para **upload de nota fiscal em PDF** e extração de dados via **LLM (Gemini)**, retornando **JSON** com os campos obrigatórios (incluindo **classificação de despesa** interpretada pelos itens).

## Como rodar

### Backend (Python)

```bash
cd api
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
uvicorn main:app --reload --port 8000
```

### Frontend (React / JS)

Em outro terminal:

```bash
cd app
npm install
npm run dev
```

Acesse `http://localhost:5173`.

## O que já está entregue (Etapa 1)

- Upload de PDF no frontend
- Botão para acionar extração
- API que chama Gemini e retorna JSON validado
- Exibição do JSON extraído na tela

