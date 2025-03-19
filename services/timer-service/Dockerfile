FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create database migrations directory if it doesn't exist
RUN mkdir -p migrations

EXPOSE 3000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "run:app"]
