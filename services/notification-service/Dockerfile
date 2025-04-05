FROM python:3.11-slim

WORKDIR /app

# Add build arg to force rebuild when needed
ARG REBUILD=0

# Install system dependencies (including curl for healthcheck) and Python dependencies
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y curl --no-install-recommends && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# Make sure Werkzeug version is compatible with Flask
RUN pip install --no-cache-dir Werkzeug==2.2.3

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=run.py

# Create database migrations directory if it doesn't exist
RUN mkdir -p migrations

# Expose the port the app runs on
EXPOSE 3000

# Copy startup scripts
COPY start.sh /app/start.sh
COPY poll_worker.sh /app/poll_worker.sh
RUN chmod +x /app/start.sh /app/poll_worker.sh

# Run app with both web server and poller
CMD ["/app/start.sh"]
