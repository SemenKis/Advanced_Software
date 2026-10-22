FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py init_db.py ./
RUN mkdir -p /app/data
EXPOSE 5002
CMD ["sh", "-c", "if [ ! -f /app/data/inventory.db ]; then python init_db.py; fi; exec python app.py"]
