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

# Create database migrations directory if it doesn't exist
RUN mkdir -p migrations

EXPOSE 5000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
