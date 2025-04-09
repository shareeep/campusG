#!/bin/bash
# poll_worker.sh - Script to run the Kafka polling worker
# This script runs in the background in the Docker container

echo "Starting Kafka polling worker at $(date)"

# Set default polling interval if not specified
KAFKA_POLL_INTERVAL_SECONDS=${KAFKA_POLL_INTERVAL_SECONDS:-10}

# Make sure we're using the correct Flask app
export FLASK_APP=run.py

# Run the polling loop
while true; do
  echo "Polling Kafka at $(date)"
  
  # Run the Flask command to poll Kafka once - use python directly to ensure app context
  cd /app && python -c "
from app import create_app
from app.services.poll_service import poll_kafka_once
app = create_app()
with app.app_context():
    print('Polling Kafka within application context')
    messages = poll_kafka_once()
    print(f'Processed {messages} messages')
"
  
  echo "Sleeping for ${KAFKA_POLL_INTERVAL_SECONDS} seconds..."
  sleep ${KAFKA_POLL_INTERVAL_SECONDS}
done
