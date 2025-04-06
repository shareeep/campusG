# Notification Service Test Plan

This document outlines the testing strategy for the notification service Kafka integration.

## Prerequisites

Before running any tests, ensure the following:

1. Kafka broker is running and accessible
2. Notification service database is running and accessible
3. Notification service is running with Kafka polling enabled

## Test Types

### 1. Basic Connectivity Tests

- **Verify Kafka Connection**
  ```bash
  python test_kafka_consumer.py
  ```
  This script tests basic connectivity to Kafka by sending test messages to various topics.

### 2. End-to-End Integration Test

- **Verify Notification Message Capture**
  ```bash
  python test_notification_kafka_integration.py
  ```
  This script tests the complete flow: sending a message from a simulated service to Kafka and verifying the notification service captures it.

### 3. Manual API Tests

- **Verify API Endpoints**
  ```bash
  python test_api.py
  ```
  Tests the REST API endpoints for sending and retrieving notifications.

## Docker Testing

### Testing in Docker Environment

Run the following commands to test in a Docker environment:

```bash
# Ensure all services are running
docker-compose up -d

# Test notification Kafka integration
docker-compose exec notification-service python test_notification_kafka_integration.py

# Test basic API functionality
docker-compose exec notification-service python test_api.py

# Check service logs for any errors
docker-compose logs notification-service
```

## Troubleshooting

If tests fail, check the following:

### 1. Kafka Polling Issues

- Verify that the Kafka polling thread is running:
  ```bash
  docker-compose exec notification-service ps aux | grep poll
  ```

- Check if the polling is working by manually running the poll command:
  ```bash
  docker-compose exec notification-service flask poll-kafka
  ```

- Check Kafka topic existence and permission:
  ```bash
  docker-compose exec kafka kafka-topics.sh --list --bootstrap-server kafka:9092
  ```

### 2. Database Connectivity

- Verify database connection:
  ```bash
  docker-compose exec notification-service psql $DATABASE_URL -c "SELECT 1"
  ```

- Check if Kafka offsets are being stored:
  ```bash
  docker-compose exec notification-service psql $DATABASE_URL -c "SELECT * FROM kafka_offsets"
  ```

### 3. Message Formats

If messages aren't being captured, check if the message format matches what the notification service expects:

- Messages should have a `type` field
- Messages should have a `payload` or equivalent content
- Messages should have a `correlation_id` for tracking

## Verifying Poll-Based Approach

To verify the poll-based approach is working correctly:

1. Stop the notification service
2. Send messages to Kafka while the service is down
3. Start the notification service
4. Verify the service catches up and processes all missed messages

## Performance Testing

To test performance under load:

```bash
# Generate high volume of messages
python test_kafka_consumer.py --count 1000 --interval 0.01

# Check database for captured messages
docker-compose exec notification-service psql $DATABASE_URL -c "SELECT COUNT(*) FROM notifications"
```

## Security Testing

- Test with malformed messages to ensure robust handling
- Test with very large messages to check for buffer overflow issues
- Verify database connection pooling under high load
