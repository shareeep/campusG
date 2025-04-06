# Notification Service Implementation Guide

This document provides comprehensive guidance on implementing the notification service for the CampusG platform using a Kafka polling approach.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [Application Structure](#application-structure)
4. [Kafka Integration](#kafka-integration)
5. [Polling Implementation](#polling-implementation)
6. [API Endpoints](#api-endpoints)
7. [Deployment](#deployment)
8. [Testing](#testing)
9. [Example Code](#example-code)

## Architecture Overview

The notification service is designed as a passive listener that records all inter-service communication in the CampusG system. Unlike other services that actively participate in business processes, the notification service's primary role is to maintain a comprehensive log of all events for auditing, debugging, and potentially user notification purposes.

```
┌─────────────────┐    ┌────────────────┐
│                 │    │                │
│  Kafka Topics   │◄───┤ Microservices  │
│                 │    │                │
└────────┬────────┘    └────────────────┘
         │
         │  Polls every X seconds
         ▼
┌─────────────────┐    ┌────────────────┐
│                 │    │                │
│  Notification   │    │  Notification  │
│   Service       ├───►│   Database     │
│                 │    │                │
└─────────────────┘    └────────────────┘
         │
         │  REST API
         ▼
┌─────────────────┐
│                 │
│    Clients      │
│                 │
└─────────────────┘
```

### Key Design Principles

1. **Reliability Over Speed**: The service prioritizes capturing all messages reliably over real-time processing.
2. **Passive Observer**: It doesn't participate in business processes or modify system state.
3. **Efficient Resource Usage**: The polling approach ensures efficient resource utilization.
4. **Resilience**: The service recovers gracefully from failures, ensuring no messages are lost.

## Database Schema

The database schema is designed to store all types of events with flexible metadata:

```sql
CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(255) NULL,
    runner_id VARCHAR(255) NULL,
    order_id VARCHAR(255) NULL,
    event JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'captured',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Kafka metadata
    source_topic VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    correlation_id VARCHAR(255) NULL,
    source_service VARCHAR(255) NULL,
    
    -- Indexes for efficient querying
    INDEX idx_customer_id (customer_id),
    INDEX idx_order_id (order_id),
    INDEX idx_created_at (created_at),
    INDEX idx_event_type (event_type),
    INDEX idx_correlation_id (correlation_id)
);

-- Table to track Kafka consumer offsets
CREATE TABLE kafka_offsets (
    topic VARCHAR(255) NOT NULL,
    partition INT NOT NULL,
    offset BIGINT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (topic, partition)
);
```

## Application Structure

The notification service follows a standard Flask application structure:

```
notification-service/
├── Dockerfile
├── requirements.txt
├── run.py                     # Main application entry point
├── app/
│   ├── __init__.py            # Flask app initialization
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py          # Database models
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # API endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── kafka_service.py   # Kafka client
│   │   └── poll_service.py    # Polling implementation
│   └── config.py              # Application configuration
├── migrations/                # Database migrations
└── tests/                     # Unit and integration tests
```

## Kafka Integration

### Configuration

The notification service connects to Kafka with the following configuration:

```python
# Configuration variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
CONSUMER_GROUP_ID = 'notification-service-group'
KAFKA_POLL_INTERVAL_SECONDS = int(os.getenv('KAFKA_POLL_INTERVAL_SECONDS', '10'))
```

### Topics to Monitor

The service should monitor all event topics used in the system:

```python
KAFKA_TOPICS = [
    "user-events", 
    "order-events", 
    "payment-events", 
    "escrow-events", 
    "scheduler-events",
    "saga-events",
    "notification-events",
    "order_events",  # Include both naming conventions (with - and _)
    "payment_events",
    "user_events"
]
```

## Polling Implementation

Instead of continuously running a thread that consumes from Kafka, the notification service uses a polling approach:

1. A scheduled process runs at regular intervals (e.g., every 10 seconds)
2. It fetches the latest offsets from the database
3. Creates a Kafka consumer starting from those offsets
4. Polls for new messages
5. Processes and stores them in the database
6. Updates the offset records
7. Closes the consumer

### Polling Script

Create a Flask CLI command to handle polling:

```python
# In app/cli.py
import click
from flask.cli import with_appcontext
from app.services.poll_service import poll_kafka_once

@click.command('poll-kafka')
@with_appcontext
def poll_kafka_command():
    """Poll Kafka for new messages and save to the database."""
    click.echo('Polling Kafka for new messages...')
    messages_processed = poll_kafka_once()
    click.echo(f'Processed {messages_processed} messages')

# Register the command with Flask
def init_app(app):
    app.cli.add_command(poll_kafka_command)
```

### Scheduler Configuration

Set up a cron job or similar scheduler to run the polling command at regular intervals:

**Crontab example**:
```
# Run every 10 seconds
* * * * * cd /path/to/notification-service && flask poll-kafka
* * * * * sleep 10 && cd /path/to/notification-service && flask poll-kafka
* * * * * sleep 20 && cd /path/to/notification-service && flask poll-kafka
* * * * * sleep 30 && cd /path/to/notification-service && flask poll-kafka
* * * * * sleep 40 && cd /path/to/notification-service && flask poll-kafka
* * * * * sleep 50 && cd /path/to/notification-service && flask poll-kafka
```

**Kubernetes CronJob example**:
```yaml
apiVersion: batch/v1beta1
kind: CronJob
metadata:
  name: notification-service-poll
spec:
  schedule: "*/1 * * * *"  # Every minute
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: poll-job
            image: notification-service:latest
            command: ["flask", "poll-kafka"]
          restartPolicy: OnFailure
```

## API Endpoints

The notification service provides REST APIs to access the notification data:

### Health Check
- `GET /health`
  - Returns the service health status
  - Status: 200 OK if healthy

### Get Notifications for an Order
- `GET /order/{orderId}`
  - Returns all notifications for a specific order ID
  - Parameters: 
    - `orderId`: The ID of the order
  - Response: Array of notification objects

### Get Latest Order Status
- `GET /order/{orderId}/latest`
  - Returns the latest notification for a specific order ID
  - Parameters:
    - `orderId`: The ID of the order
  - Response: Latest notification object

### Get Notifications for a Customer
- `GET /customer/{customerId}/notifications`
  - Returns all notifications for a specific customer
  - Parameters:
    - `customerId`: The ID of the customer
    - `limit`: (optional) Maximum number of notifications to return
    - `offset`: (optional) Pagination offset
  - Response: Array of notification objects

### Create Manual Notification
- `POST /send-notification`
  - Creates a manual notification
  - Request Body:
    ```json
    {
        "customerId": "customer-123",
        "runnerId": "runner-456",  // Optional
        "orderId": "order-789",
        "event": "Your order has been placed"
    }
    ```
  - Response: Created notification object

## Deployment

### Docker Configuration

The notification service is containerized using Docker:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV FLASK_APP=run.py
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV KAFKA_POLL_INTERVAL_SECONDS=10
ENV DATABASE_URL=postgresql://postgres:postgres@notification-db:5432/notification_db

# Create a non-root user to run the app
RUN useradd -m notifuser
USER notifuser

# Command to run the web server
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "run:app"]
```

### Docker Compose Integration

```yaml
services:
  notification-db:
    image: postgres:14
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: notification_db
    volumes:
      - notification_db_data:/var/lib/postgresql/data
    ports:
      - "5437:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
      
  notification-service:
    build:
      context: ./services/notification-service
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@notification-db:5432/notification_db
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - KAFKA_POLL_INTERVAL_SECONDS=10
    depends_on:
      notification-db:
        condition: service_healthy
      kafka:
        condition: service_healthy
    ports:
      - "3006:3000"
```

### Poll Script for Docker

Create a script to run inside the container that handles polling:

```bash
#!/bin/bash
# poll_worker.sh
while true; do
  echo "Polling Kafka at $(date)"
  flask poll-kafka
  echo "Sleeping for $KAFKA_POLL_INTERVAL_SECONDS seconds..."
  sleep $KAFKA_POLL_INTERVAL_SECONDS
done
```

Update the Dockerfile to include:

```dockerfile
# Add polling script
COPY poll_worker.sh /app/poll_worker.sh
RUN chmod +x /app/poll_worker.sh

# Command to run the web server and polling in the background
CMD ["sh", "-c", "/app/poll_worker.sh & gunicorn --bind 0.0.0.0:3000 run:app"]
```

## Testing

### Unit Tests

Create unit tests for the notification service components:

```python
# test_models.py
def test_notification_model():
    notification = Notifications(
        customer_id="test-customer",
        order_id="test-order",
        event=json.dumps({"message": "Test event"}),
        source_topic="test-topic",
        event_type="test.event",
        correlation_id="test-correlation",
        source_service="test-service"
    )
    assert notification.customer_id == "test-customer"
    assert notification.order_id == "test-order"
    # More assertions...
```

### Integration Tests

Create integration tests to verify Kafka integration:

```python
# test_kafka_integration.py
def test_kafka_poll():
    # Set up test environment
    with app.app_context():
        # Clear existing offsets
        db.session.query(KafkaOffsets).delete()
        db.session.commit()
        
        # Send test message to Kafka
        producer = create_test_producer()
        test_message = create_test_message()
        producer.send('test-topic', test_message)
        producer.flush()
        
        # Run polling
        poll_kafka_once()
        
        # Verify message was captured
        notification = Notifications.query.filter_by(
            correlation_id=test_message['correlation_id']
        ).first()
        
        assert notification is not None
        assert notification.event_type == test_message['type']
        # More assertions...
```

## Example Code

### Polling Service Implementation

```python
# app/services/poll_service.py
from kafka import KafkaConsumer, TopicPartition
from app.models.models import Notifications, KafkaOffsets
from app import db
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_stored_offsets():
    """Retrieve the latest consumed offsets from the database."""
    offsets = {}
    stored_offsets = KafkaOffsets.query.all()
    
    for offset in stored_offsets:
        if offset.topic not in offsets:
            offsets[offset.topic] = {}
        offsets[offset.topic][offset.partition] = offset.offset
        
    return offsets

def update_stored_offset(topic, partition, offset):
    """Update the stored offset for a topic-partition."""
    stored_offset = KafkaOffsets.query.filter_by(
        topic=topic, 
        partition=partition
    ).first()
    
    if stored_offset:
        stored_offset.offset = offset
        stored_offset.updated_at = datetime.utcnow()
    else:
        stored_offset = KafkaOffsets(
            topic=topic,
            partition=partition,
            offset=offset
        )
        db.session.add(stored_offset)
        
    db.session.commit()

def poll_kafka_once():
    """
    Poll Kafka once for new messages and save them to the database.
    Returns the number of messages processed.
    """
    from app.config import KAFKA_BOOTSTRAP_SERVERS, CONSUMER_GROUP_ID, KAFKA_TOPICS
    
    logger.info("Starting Kafka polling cycle")
    messages_processed = 0
    
    try:
        # Get stored offsets
        stored_offsets = get_stored_offsets()
        
        # Create consumer without subscribing yet
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP_ID,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
        )
        
        # Get partition metadata for all topics
        topics_metadata = consumer.topics()
        
        # Ensure our topics exist 
        existing_topics = [topic for topic in KAFKA_TOPICS if topic in topics_metadata]
        if not existing_topics:
            logger.warning(f"None of the configured topics exist: {KAFKA_TOPICS}")
            consumer.close()
            return 0
            
        # Get partitions for each topic
        partitions = []
        for topic in existing_topics:
            topic_partitions = consumer.partitions_for_topic(topic)
            if not topic_partitions:
                logger.warning(f"No partitions found for topic {topic}")
                continue
                
            for partition in topic_partitions:
                tp = TopicPartition(topic, partition)
                
                # If we have a stored offset, seek to it + 1
                if (topic in stored_offsets and 
                        partition in stored_offsets[topic]):
                    offset = stored_offsets[topic][partition] + 1
                    consumer.assign([tp])
                    consumer.seek(tp, offset)
                
                partitions.append(tp)
                
        # Assign all partitions
        consumer.assign(partitions)
        
        # Poll for messages
        poll_results = consumer.poll(timeout_ms=5000, max_records=500)
        
        # Process messages
        for tp, messages in poll_results.items():
            topic = tp.topic
            partition = tp.partition
            
            for message in messages:
                try:
                    # Extract message data
                    message_data = message.value
                    event_type = message_data.get('type', 'unknown')
                    payload = message_data.get('payload', message_data)
                    correlation_id = message_data.get('correlation_id', '')
                    source_service = message_data.get('source', 'unknown')
                    
                    # Extract IDs with fallbacks for different naming conventions
                    customer_id = str(payload.get('customer_id', payload.get('customerId', '')))
                    runner_id = str(payload.get('runner_id', payload.get('runnerId', '')))
                    order_id = str(payload.get('order_id', payload.get('orderId', '')))
                    
                    # Format event info
                    event_info = {
                        'topic': topic,
                        'event_type': event_type,
                        'correlation_id': correlation_id,
                        'source_service': source_service,
                        'timestamp': datetime.utcnow().isoformat(),
                        'payload': payload
                    }
                    
                    # Create notification
                    notification = Notifications(
                        customer_id=customer_id if customer_id not in ('None', 'null', '') else '',
                        runner_id=runner_id if runner_id not in ('None', 'null', '') else None,
                        order_id=order_id if order_id not in ('None', 'null', '') else '',
                        event=json.dumps(event_info),
                        status='captured',
                        source_topic=topic,
                        event_type=event_type,
                        correlation_id=correlation_id,
                        source_service=source_service
                    )
                    
                    db.session.add(notification)
                    
                    # Update stored offset
                    update_stored_offset(topic, partition, message.offset)
                    
                    messages_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    db.session.rollback()
                
            # Commit session after processing batch for partition
            try:
                db.session.commit()
            except Exception as e:
                logger.error(f"Error committing session: {e}", exc_info=True)
                db.session.rollback()
                
        consumer.close()
        logger.info(f"Kafka polling cycle completed, processed {messages_processed} messages")
        return messages_processed
        
    except Exception as e:
        logger.error(f"Error in poll_kafka_once: {e}", exc_info=True)
        return 0
```

### Database Models

```python
# app/models/models.py
from app import db
from datetime import datetime
import uuid
import json

class Notifications(db.Model):
    """Database model for notifications."""
    __tablename__ = "notifications"
    
    notification_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(255), nullable=True, index=True, default="")
    runner_id = db.Column(db.String(255), nullable=True, index=True)
    order_id = db.Column(db.String(255), nullable=True, index=True, default="")
    event = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="captured")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Kafka metadata
    source_topic = db.Column(db.String(255), nullable=True)
    event_type = db.Column(db.String(255), nullable=True)
    correlation_id = db.Column(db.String(255), nullable=True)
    source_service = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        """Convert the model to a dictionary."""
        # Try to parse event JSON if it's a string
        event_data = self.event
        try:
            if isinstance(self.event, str):
                event_data = json.loads(self.event)
        except:
            # Keep as is if it can't be parsed
            pass
            
        return {
            "notificationId": self.notification_id,
            "customerId": self.customer_id,
            "runnerId": self.runner_id,
            "orderId": self.order_id,
            "event": event_data,
            "status": self.status,
            "createdAt": self.created_at.isoformat(),
            "sourceTopic": self.source_topic,
            "eventType": self.event_type,
            "correlationId": self.correlation_id,
            "sourceService": self.source_service
        }

class KafkaOffsets(db.Model):
    """Track Kafka consumer offsets."""
    __tablename__ = "kafka_offsets"
    
    topic = db.Column(db.String(255), primary_key=True)
    partition = db.Column(db.Integer, primary_key=True)
    offset = db.Column(db.BigInteger, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### Main Application Setup

```python
# run.py
from app import create_app
import os
import subprocess
import threading

app = create_app()

if __name__ == "__main__":
    # Start polling in the background if not in testing mode
    if os.environ.get('FLASK_ENV') != 'testing':
        # Start the polling script in a separate process
        polling_process = None
        if os.environ.get('ENABLE_KAFKA_POLLING', 'true').lower() == 'true':
            polling_cmd = ['bash', '-c', '/app/poll_worker.sh']
            polling_process = subprocess.Popen(polling_cmd)
            print(f"Started Kafka polling process with PID {polling_process.pid}")
    
    # Run the Flask app
    app.run(host="0.0.0.0", port=3000)
```

---

By following this implementation guide, you'll have a robust notification service that reliably captures all Kafka messages using a polling approach, avoiding the application context issues that can occur with threaded Kafka consumers in Flask applications.
