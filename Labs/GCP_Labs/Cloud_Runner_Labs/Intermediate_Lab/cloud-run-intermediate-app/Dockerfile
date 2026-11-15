# 27 million New York complaints, now in a box
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects PORT (8080 by default)
CMD exec gunicorn -b 0.0.0.0:${PORT:-8080} app:app
