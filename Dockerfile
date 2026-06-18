FROM python:3.12-slim

WORKDIR /app

# Copia o requirements.txt de dentro da pasta api/
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o conteúdo da pasta api/ para a pasta de trabalho (/app)
COPY api/ .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
