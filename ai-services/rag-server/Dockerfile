FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY corpus_sources/ ./corpus_sources/
COPY corpus/ ./corpus/

ENV PYTHONUNBUFFERED=1
ENV PORT=5003

EXPOSE 5003

CMD ["python", "rag_http_server.py"]
