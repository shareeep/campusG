FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install system dependencies (including curl for healthcheck) and Python dependencies
RUN apt-get update && \
    apt-get install -y curl --no-install-recommends && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

COPY . .

ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1

EXPOSE 3000

CMD ["flask", "run", "--host=0.0.0.0", "--port=3000"]
