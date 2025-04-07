FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1

EXPOSE 3000

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Use entrypoint script that runs migrations before starting the app
CMD ["/app/entrypoint.sh"]
