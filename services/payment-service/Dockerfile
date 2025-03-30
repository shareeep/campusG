FROM python:3.11-slim

WORKDIR /app

# Add build arg to force rebuild when needed
ARG REBUILD=0

# Install dependencies
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

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

# Make sure script is executable
RUN chmod +x ./entrypoint.sh

# Use entrypoint script to handle migrations before starting the app
ENTRYPOINT ["./entrypoint.sh"]
