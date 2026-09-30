FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY database/ ./database/

ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/database/transportation.db
ENV OLLAMA_URL=http://ollama:11434
ENV OLLAMA_MODEL=qwen2.5:0.5b

EXPOSE 5004

WORKDIR /app/backend

CMD ["python", "app.py"]