#!/bin/bash

# Start the polling worker in the background
if [ "$ENABLE_KAFKA_POLLING" != "false" ]; then
  echo "Starting Kafka polling worker..."
  if [ -f /app/poll_worker.sh ]; then
    /app/poll_worker.sh &
  else
    echo "Warning: poll_worker.sh not found"
    # Fallback to direct Python with proper app context
    (
    while true; do
      echo "Polling Kafka at $(date)"
      # Run with proper app context
      python -c "
from app import create_app
from app.services.poll_service import poll_kafka_once
app = create_app()
with app.app_context():
    print('Polling Kafka within application context')
    messages = poll_kafka_once()
    print(f'Processed {messages} messages')
" || echo "Poll failed"
      echo "Sleeping for 10 seconds..."
      sleep 10
    done
    ) &
  fi
else
  echo "Kafka polling disabled"
fi

# Start the web server
exec gunicorn --bind 0.0.0.0:3000 --workers 2 --threads 4 run:app
