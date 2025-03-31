# Create Order Saga Orchestrator Testing Guide

This document outlines strategies for testing the Create Order Saga Orchestrator, which orchestrates the order creation workflow using Kafka messages.

## Setup for Testing

1. Ensure all required services are running:
   ```bash
   docker-compose up -d zookeeper kafka create-order-saga-db create-order-saga-orchestrator
   ```

2. Verify the service is running:
   ```bash
   docker ps | grep create-order-saga-orchestrator
   ```

## Important Note on Kafka Connectivity

The Create Order Saga Orchestrator uses `kafka-python` for Kafka connectivity. There are two different bootstrap server addresses depending on where you run the tests:

- **Inside Docker containers**: Use `kafka:9092` (Docker network name)
- **From host machine**: Use `localhost:9092` (Port exposed to host)

Our test scripts are configured to use the appropriate address based on their context.

## Testing Approaches

### 1. API Testing

You can test the API endpoints directly:

#### Start a new saga:

```bash
curl -X POST http://localhost:3101/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_123",
    "order_details": {
      "foodItems": [
        {
          "name": "Burger",
          "price": 12.99,
          "quantity": 1
        },
        {
          "name": "Fries", 
          "price": 4.99,
          "quantity": 1
        }
      ],
      "deliveryLocation": "North Campus"
    }
  }'
```

This will return a saga ID that you can use to track the saga state:
```json
{
  "message": "Saga started successfully",
  "saga_id": "7e183609-c089-40b6-b309-dbbb78d567dd",
  "status": "STARTED",
  "success": true
}
```

#### Check saga status:

```bash
curl http://localhost:3101/api/sagas/YOUR_SAGA_ID
```

#### List all sagas:

```bash
curl http://localhost:3101/api/sagas
```

### 2. Automated Test Script (Host Machine)

The `test_create_order_saga.sh` script automates the process of testing a full saga flow from the host machine:

```bash
cd services/create-order-saga-orchestrator
bash test_create_order_saga.sh
```

This script:
1. Starts a new saga via the API
2. Simulates events from other services using the Kafka producer
3. Checks the final saga state to verify completion

### 3. Docker Container Testing

For testing directly within the Docker container:

```bash
# Copy the test script to the container
docker cp services/create-order-saga-orchestrator/docker_test_saga.sh campusg-create-order-saga-orchestrator-1:/app/

# Execute the test in the container
docker exec -it campusg-create-order-saga-orchestrator-1 bash /app/docker_test_saga.sh
```

This is useful for testing in an environment identical to production.

### 4. Python-based Testing

For more complex test scenarios, use the Python test scripts:

```bash
# Simple test for Kafka connectivity
cd services/create-order-saga-orchestrator
python test_saga.py

# Comprehensive test of the full saga flow
python complete_test.py
```

These scripts provide more detailed output and better error handling than the bash scripts.

### 5. Manual Event Simulation with Kafka Producer

For fine-grained testing, use the `kafka_test_producer.py` script to simulate individual events:

```bash
# Simulate Order Service creating an order
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event order.created --correlation-id YOUR_SAGA_ID --order-id YOUR_ORDER_ID

# Simulate User Service retrieving payment info
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event user.payment_info_retrieved --correlation-id YOUR_SAGA_ID

# Simulate Payment Service authorizing payment
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event payment.authorized --correlation-id YOUR_SAGA_ID --order-id YOUR_ORDER_ID

# Simulate Order Service updating order status
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event order.status_updated --correlation-id YOUR_SAGA_ID --order-id YOUR_ORDER_ID

# Simulate Timer Service starting the timer
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event timer.started --correlation-id YOUR_SAGA_ID --order-id YOUR_ORDER_ID
```

### 6. Kafka Message Inspection

To inspect messages being sent to Kafka:

```bash
# View messages on the order_commands topic
docker exec -it campusg-kafka-1 kafka-console-consumer --bootstrap-server localhost:9092 --topic order_commands --from-beginning

# List all Kafka topics
docker exec -it campusg-kafka-1 kafka-topics --bootstrap-server localhost:9092 --list
```

### 7. Failure Scenario Testing

Test how the orchestrator handles failures:

```bash
# Simulate failed order creation
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event order.creation_failed --correlation-id YOUR_SAGA_ID

# Simulate failed payment info retrieval
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event user.payment_info_failed --correlation-id YOUR_SAGA_ID

# Simulate failed payment authorization
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event payment.failed --correlation-id YOUR_SAGA_ID

# Simulate failed order status update
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event order.status_update_failed --correlation-id YOUR_SAGA_ID --order-id YOUR_ORDER_ID

# Simulate failed timer start
python kafka_test_producer.py --bootstrap-servers localhost:9092 --event timer.failed --correlation-id YOUR_SAGA_ID --order-id YOUR_ORDER_ID
```

## Monitoring

### Logs

Monitor the orchestrator's logs to see the saga progression and any errors:

```bash
docker logs -f campusg-create-order-saga-orchestrator-1
```

### Kafka Service Status

Check if the Kafka client is properly connected:

```bash
docker exec campusg-create-order-saga-orchestrator-1 python -c "from app.services.kafka_service import kafka_client; print(f'Producer connected: {kafka_client.producer is not None}, Consumer connected: {kafka_client.consumer is not None}')"
```

## Troubleshooting

### 1. Kafka Connection Issues

If you're having trouble connecting to Kafka, verify that:

- Kafka is running: `docker ps | grep kafka`
- Zookeeper is running: `docker ps | grep zookeeper`
- The bootstrap server address is correct for your context (inside Docker vs. host machine)
- Kafka topics exist: `docker exec -it campusg-kafka-1 kafka-topics --bootstrap-server localhost:9092 --list`

### 2. API Connection Issues

If the API is not responding:

- Check if the service is running: `docker ps | grep create-order-saga-orchestrator`
- Verify the port mapping: `docker port campusg-create-order-saga-orchestrator-1`
- Check service logs for errors: `docker logs campusg-create-order-saga-orchestrator-1`

### 3. Event Processing Issues

If events aren't being processed:

- Verify the Kafka consumer is subscribed to the correct topics
- Check the correlation ID is correct in all messages
- Ensure events are being sent in the correct order
- Look for errors in the service logs

### 4. Database Issues

If encountering database errors:

```bash
# Initialize the database
docker exec -it campusg-create-order-saga-orchestrator-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"

# Check database connectivity
docker exec -it campusg-create-order-saga-orchestrator-1 bash -c "python -c 'import psycopg2; conn=psycopg2.connect(\"dbname=create_order_saga_db user=postgres password=postgres host=create-order-saga-db\"); print(\"Connected!\")'"
```

## Next Steps

- Add more comprehensive integration tests
- Implement cancellation and compensation testing
- Add performance testing with multiple concurrent sagas
