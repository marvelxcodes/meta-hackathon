FROM python:3.11-slim

WORKDIR /app
ENV CACHE_BUSTER=3

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY models.py .
COPY server/ server/
COPY client.py .
COPY __init__.py .
COPY openenv.yaml .

EXPOSE 8000



CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
