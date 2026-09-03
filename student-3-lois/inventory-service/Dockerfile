FROM python:3.11-slim

WORKDIR /app

COPY inventory-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY inventory-service ./inventory-service
COPY prompts ./prompts

EXPOSE 5001

CMD ["python", "inventory-service/app.py"]
