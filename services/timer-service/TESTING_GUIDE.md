# Timer Service Testing Guide

This guide explains how to test the Timer Service with Kafka integration.

## Prerequisites

- Docker and Docker Compose installed
- The Timer Service code has been updated with the latest changes
- The docker-compose.yml file has been updated with Kafka and Timer Service configuration

## Testing the Timer Service

### 1. Start the Required Services

First, start Kafka, Zookeeper, Timer-DB, and the Timer Service:

```bash
# Start Kafka and Zookeeper first
docker-compose up -d zookeeper kafka

# Wait a moment for Kafka to start
sleep 15

# Build and start the Timer Service and its database
docker-compose build timer-service
docker-compose up -d timer-db timer-service

# Check logs to make sure it started properly
docker-compose logs --tail=20 timer-service
```

### 2. Start the Kafka Test Consumer

Use the provided Kafka test consumer script to monitor events published to Kafka:

```bash
# Make the script executable first
chmod +x services/timer-service/kafka_test_consumer.py

# Run the consumer (Kafka is exposed on localhost:9092)
python services/timer-service/kafka_test_consumer.py

# Or if you prefer to use the Kafka CLI tools:
docker exec -it campusg-kafka-1 kafka-console-consumer --bootstrap-server localhost:9092 --topic timer-events --from-beginning
```


### 3. Create a Test Timer with 1-Minute Expiration

In a different terminal, create a test timer that will expire in 1 minute:

```bash
# Using curl (note the port is 3007 for timer-service according to docker-compose.yml)
curl -X POST http://localhost:3007/api/test-quick-timer \
  -H "Content-Type: application/json" \
  -d '{"orderId":"test-123", "customerId":"cust-456"}'

# Alternatively, you can use Postman or any API client to make this POST request
```

### 4. What to Expect

1. When you create the timer:
   - The API will return a response with the timer ID and expiration time
   - A `TIMER_STARTED` event will appear in the Kafka consumer

2. After 1 minute:
   - The scheduler will detect the expired timer
   - An `ORDER_TIMEOUT` event will be published to Kafka
   - This event will appear in the Kafka consumer

3. The `ORDER_TIMEOUT` event will have a payload similar to:
   ```json
   {
     "type": "ORDER_TIMEOUT",
     "payload": {
       "timerId": "some-uuid",
       "orderId": "test-123",
       "customerId": "cust-456",
       "expiresAt": "2025-03-25T08:52:00.000Z"
     },
     "timestamp": "2025-03-25T08:52:00.000Z"
   }
   ```

### 5. Testing Other Timer Operations

You can also test other timer operations:

#### Stop a Timer (Simulate Runner Acceptance)

```bash
curl -X POST http://localhost:3007/api/stop-request-timer \
  -H "Content-Type: application/json" \
  -d '{"orderId":"test-123", "runnerId":"runner-789"}'
```

#### Cancel a Timer

```bash
curl -X POST http://localhost:3007/api/cancel-timer \
  -H "Content-Type: application/json" \
  -d '{"orderId":"test-123"}'
```

#### Manually Trigger Timeout Check

```bash
curl -X GET http://localhost:3007/api/check-order-timeout
```

#### Check Timer Status

```bash
curl -X GET http://localhost:3007/api/timers/order/test-123
```

## Troubleshooting

### Kafka Connection Issues

If the Timer Service can't connect to Kafka:

1. Check that Kafka is running:
   ```bash
   docker-compose ps kafka
   ```

2. Verify the Kafka bootstrap servers configuration:
   - In a Docker setup, the Timer Service should use `kafka:9092` as the bootstrap server.
   - Make sure the `KAFKA_BOOTSTRAP_SERVERS` environment variable is set correctly in docker-compose.yml.

3. Check the Timer Service logs for Kafka connection errors:
   ```bash
   docker-compose logs timer-service | grep -i kafka
   ```

### Initial Database Setup

If you see database errors when starting the Timer Service:

1. Make sure the migrations have been applied:
   ```bash
   docker exec -it campusg-timer-service-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   ```

### Timer Not Expiring

If you don't see timeout events:

1. Check if the scheduler is running by looking at the logs:
   ```bash
   docker-compose logs --tail=50 timer-service | grep scheduler
   ```

2. Manually trigger a timeout check:
   ```bash
   curl -X GET http://localhost:3007/api/check-order-timeout
   ```

3. Verify that there are unexpired timers in the database:
   ```bash
   curl -X GET http://localhost:3007/api/timers/order/test-123
   ```
