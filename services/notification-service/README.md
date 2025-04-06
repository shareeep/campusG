# Notification Service

A microservice that captures and stores all events from Kafka, serving as a centralized event logging system.

## Overview

The notification service listens to all Kafka topics and logs every message as a notification in its database. This provides:

1. A complete audit trail of all system events
2. A unified way to query the status of orders across services
3. Historical data for debugging and analysis

## Kafka Integration

The notification service functions as a passive consumer of Kafka messages without publishing (write-only):

- Listens to all event topics across the system
- Captures every message regardless of the producer
- Normalizes different message formats into a consistent database schema
- Supports different naming conventions used by various services

### Topics Monitored

The service subscribes to all event topics, including but not limited to:

- `order-events` / `order_events`
- `payment-events` / `payment_events`
- `user-events` / `user_events`
- `escrow-events`
- `scheduler-events`
- `saga-events`
- `notification-events`

### Message Processing

When a message is received:

1. The message is parsed and normalized to handle different formats
2. Customer, runner, and order IDs are extracted with fallbacks for different naming conventions
3. The entire message is stored in the `notifications` table with appropriate metadata, including:
   - Source topic
   - Event type
   - Correlation ID
   - Source service
4. No response is sent back to Kafka (consumer-only design)

### Database Schema

The notification service uses an enhanced database schema to store any type of Kafka message:

- **notification_id**: Unique identifier for the notification
- **customer_id**: Customer ID (nullable, for system events)
- **runner_id**: Runner ID (nullable)
- **order_id**: Order ID (nullable, for non-order events)
- **event**: Full JSON payload of the event
- **status**: Status of the notification
- **created_at**: Timestamp when the notification was created
- **source_topic**: The Kafka topic that the message came from
- **event_type**: The type of event (from the message)
- **correlation_id**: The correlation ID for tracking
- **source_service**: The service that sent the message

This expanded schema ensures that:
- System events without customer IDs can be stored
- Non-order related events can be captured
- Messages with different formats and field names are normalized
- All metadata is preserved for better debugging and tracing

## API Endpoints

The service provides REST endpoints to query the captured notifications:

- `GET /health` - Health check endpoint
- `GET /order/<order_id>/latest` - Get the latest notification for a specific order
- `GET /order/<order_id>` - Get all notifications for a specific order
- `POST /send-notification` - Manually create a notification (for direct API usage)

## Testing

A test script is provided to verify the Kafka integration:

```bash
# Run within the Docker container
docker exec -it notification-service python test_kafka_consumer.py

# Or with a local Python environment
python test_kafka_consumer.py
```

This will send test messages to various Kafka topics that should be captured by the notification service.

## Implementation Details

The service uses a singleton pattern for the Kafka client to maintain a single connection across the application. Key implementation files:

- `app/services/kafka_service.py` - The Kafka client implementation (consumer-only)
- `app/api/notification_routes.py` - Contains the consumer logic and API endpoints
- `run.py` - Application entry point that initializes the Kafka consumer
- `test_kafka_consumer.py` - Test script for verifying the implementation

## Environment Variables

The service can be configured using the following environment variables:

- `KAFKA_BOOTSTRAP_SERVERS` - Comma-separated list of Kafka brokers (default: `kafka:9092`)
- `DATABASE_URL` - Database connection string
- `FLASK_APP` - Flask application entry point (should be set to `run.py`)
- `FLASK_DEBUG` - Enable/disable debug mode

## Deployment

The service is containerized with Docker and can be deployed using Docker Compose or Kubernetes:

```bash
# Using Docker Compose
docker-compose up -d notification-service

# Using Kubernetes
kubectl apply -f kubernetes/services/notification-service/
```

## Technical Considerations

1. **High Volume Handling**: The service is designed to handle high message volumes with proper error handling and recovery mechanisms.

2. **Database Growth**: As this service logs all events, database growth should be monitored, and a data retention policy may be needed for production environments.

3. **Consumer Group ID**: A unique consumer group ID (`notification-service-group`) ensures proper message consumption.
