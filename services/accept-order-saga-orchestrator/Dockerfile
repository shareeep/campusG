FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ENV FLASK_APP=run.py # Removed as run.py is removed
ENV PYTHONUNBUFFERED=1

EXPOSE 3000

# CMD instruction removed - command will be specified in docker-compose.yml
