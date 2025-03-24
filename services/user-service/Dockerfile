FROM python:3.9-slim

WORKDIR /app

# Add build arg to force rebuild when needed
ARG REBUILD=0

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install specific Werkzeug version that's compatible with Flask 2.2.3
RUN pip install --no-cache-dir Werkzeug==2.2.3

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=3000

# Create database migrations directory if it doesn't exist
RUN mkdir -p migrations

EXPOSE 3000

# Use a more robust command that ensures correct binding
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--log-level", "debug", "--timeout", "120", "run:app"]
