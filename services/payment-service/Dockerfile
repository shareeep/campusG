FROM python:3.11-slim

WORKDIR /app

# Add build arg to force rebuild when needed
ARG REBUILD=0

# Install necessary tools
RUN apt-get update && apt-get install -y dos2unix curl wget && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Make sure Werkzeug version is compatible with Flask
RUN pip install --no-cache-dir Werkzeug==2.2.3

# Copy application code
COPY . .

# Convert line endings and ensure script is executable
RUN dos2unix /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=run.py

# Create database migrations directory if it doesn't exist
RUN mkdir -p migrations

# Expose the port the app runs on
EXPOSE 3000

# Use entrypoint script to handle migrations before starting the app
# ENTRYPOINT ["/app/entrypoint.sh"]
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
