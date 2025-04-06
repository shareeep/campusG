# Step-by-Step Troubleshooting Guide for Create Order Saga Orchestrator

This guide provides a methodical approach to troubleshooting and testing the Create Order Saga Orchestrator. We'll work through each component incrementally, addressing issues as they arise.

## Project Context

This is a microservices system for a campus food delivery service, where the Create Order Saga Orchestrator coordinates the process when a user places an order. The flow involves several services communicating primarily through Kafka:

1. UI → Create Order Saga Orchestrator (HTTP)
2. Create Order Saga Orchestrator → Order Service (Kafka)
3. Order Service → Create Order Saga Orchestrator (Kafka)
4. Create Order Saga Orchestrator → User Service (Kafka)
5. User Service → Create Order Saga Orchestrator (Kafka)
6. Create Order Saga Orchestrator → Payment Service (Kafka)
7. Payment Service → Stripe → Payment Service → Create Order Saga Orchestrator (Kafka)
8. Create Order Saga Orchestrator → Order Service (update order status) (Kafka)
9. Order Service → Create Order Saga Orchestrator (Kafka)
10. Create Order Saga Orchestrator → Timer Service (HTTP instead of Kafka)
11. Timer Service → Create Order Saga Orchestrator (Kafka)
12. Create Order Saga Orchestrator → UI (HTTP response)

## Progress Summary

1. **Fixed Issues**:
   - Corrected Kafka configuration in `docker-compose.yml` to support connections from both inside Docker and host machine
   - Updated ports for Kafka listeners (`9092` for internal, `29092` for external)
   - Fixed message serialization in `comprehensive_test.py`

2. **Current Issues**:
   - Saga Orchestrator stays in `CREATE_ORDER` step despite events being sent to Kafka
   - Events not being processed by the Orchestrator's consumer

## Core Files

- `services/create-order-saga-orchestrator/COMPREHENSIVE_TEST_PLAN.md` - Test plan
- `services/create-order-saga-orchestrator/comprehensive_test.py` - Test script 
- `services/create-order-saga-orchestrator/app/services/saga_orchestrator.py` - Main orchestrator
- `services/create-order-saga-orchestrator/app/services/kafka_service.py` - Kafka integration
- `services/create-order-saga-orchestrator/app/api/routes.py` - API endpoints
- `services/create-order-saga-orchestrator/app/services/http_client.py` - HTTP client for timer service

## Docker Services Information

The Docker services run with these port mappings:
- Create Order Saga Orchestrator: Port 3101
- Order Service: Port 3002
- User Service: Port 3001
- Payment Service: Port 3003
- Timer Service: Port 3007
- Notification Service: Port 3006
- Kafka: Port 9092 (internal), 29092 (external)

## Step-by-Step Troubleshooting Plan

### 1. Verify Environment Setup

First, let's check if all services are running correctly:

```bash
docker-compose ps
```

Check logs for each service to identify any startup errors:

```bash
docker-compose logs create-order-saga-orchestrator --tail=50
docker-compose logs kafka --tail=50
```

### 2. Verify Kafka Configuration

Examine the Kafka service configuration in the orchestrator:

```bash
docker-compose exec create-order-saga-orchestrator cat /app/config.py
```

Check if the Kafka bootstrap servers are configured correctly inside the container:

```bash
docker-compose exec create-order-saga-orchestrator env | grep KAFKA
```

### 3. Examine Kafka Consumers

Check if the Kafka consumers in the orchestrator are properly configured:

```bash
docker-compose exec create-order-saga-orchestrator python -c "from app.services.kafka_service import kafka_client; print(kafka_client.consumer.subscription() if kafka_client and kafka_client.consumer else 'No consumer or not subscribed')"
```

Verify if topics exist and are properly configured:

```bash
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### 4. Test Basic Connectivity

Test if the orchestrator is reachable via HTTP:

```bash
curl -X GET http://localhost:3101/health
```

Test a simple saga creation:

```bash
curl -X POST http://localhost:3101/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "test_customer", "order_details": {"foodItems": [{"name": "Test Burger", "price": 10.99, "quantity": 1}], "deliveryLocation": "Test Location"}, "payment_amount": 10.99}'
```

### 5. Debug Kafka Messages

Let's check if messages are being sent to the right topics and in the correct format:

```bash
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic order-events --from-beginning
```

In another terminal, send a test message:

```bash
cd services/create-order-saga-orchestrator && python -c "from kafka import KafkaProducer; import json; producer = KafkaProducer(bootstrap_servers='localhost:29092', value_serializer=lambda v: json.dumps(v).encode('utf-8')); producer.send('order-events', {'type': 'test-event', 'correlation_id': 'test-id', 'payload': {'test': 'data'}})"
```

### 6. Monitor Orchestrator During Test

Start container logs monitoring:

```bash
docker-compose logs -f create-order-saga-orchestrator
```

In a separate terminal, run the test script:

```bash
cd services/create-order-saga-orchestrator && python comprehensive_test.py --docker
```

Watch the logs to see how the orchestrator reacts to each incoming message.

### 7. Inspect Saga State Database

Check the database to see if saga state is being updated:

```bash
docker-compose exec create-order-saga-db psql -U postgres -d create_order_saga_db -c "SELECT * FROM create_order_saga_state ORDER BY created_at DESC LIMIT 5;"
```

### 8. Test Individual Components

#### 8.1 Create Order Step

Test just the first step by sending an order.created event:

```bash
# Run from host machine
cd services/create-order-saga-orchestrator && python -c "from kafka import KafkaProducer; import json, uuid; producer = KafkaProducer(bootstrap_servers='localhost:29092', value_serializer=lambda v: json.dumps(v).encode('utf-8')); saga_id = str(uuid.uuid4()); print(f'Saga ID: {saga_id}'); producer.send('order-events', {'type': 'order.created', 'correlation_id': saga_id, 'payload': {'order_id': 'test-order-1', 'customer_id': 'test-customer', 'status': 'PENDING_PAYMENT'}})"
```

Wait a moment, then check the saga state:

```bash
docker-compose exec create-order-saga-db psql -U postgres -d create_order_saga_db -c "SELECT id, status, current_step, order_id FROM create_order_saga_state ORDER BY created_at DESC LIMIT 1;"
```

#### 8.2 Payment Info Step

If you see a saga record, continue with the payment info step:

```bash
cd services/create-order-saga-orchestrator && python -c "from kafka import KafkaProducer; import json; producer = KafkaProducer(bootstrap_servers='localhost:29092', value_serializer=lambda v: json.dumps(v).encode('utf-8')); producer.send('user-events', {'type': 'user.payment_info_retrieved', 'correlation_id': 'YOUR_SAGA_ID', 'payload': {'payment_info': {'card_type': 'visa', 'last_four': '4242', 'card_token': 'tok_visa'}}})"
```

Replace `YOUR_SAGA_ID` with the saga ID from the previous step.

### 9. Examine Code Issues

If the events are not being processed, examine the Kafka consumer implementation:

```bash
docker-compose exec create-order-saga-orchestrator cat /app/services/kafka_service.py
```

Look for:
- Consumer group configuration
- Topic subscription methods
- Message deserialization
- Event handler registration

### 10. Restart and Re-test

After making any changes, restart the service:

```bash
docker-compose restart create-order-saga-orchestrator
```

Then run the test script again:

```bash
cd services/create-order-saga-orchestrator && python comprehensive_test.py --docker
```

## Common Issues and Solutions

### 1. Message Format Issues

Ensure the message format being sent matches what the consumer expects:
- Check value serializers in both the test script and the orchestrator
- Verify correlation_id field is properly set in all messages
- Check if any required fields are missing from test messages

### 2. Kafka Connection Issues

If Kafka connections fail:
- Verify ports and listener configurations in docker-compose.yml
- Check if the bootstrap servers configuration is consistent across services
- Ensure Kafka is healthy and topics are correctly created

### 3. Event Handler Registration

If events are delivered but not processed:
- Verify event handlers are properly registered with the Kafka service
- Check if the orchestrator is correctly initialized
- Look for errors in the handler functions

### 4. State Tracking Issues

If saga state doesn't update correctly:
- Examine the database schema and migrations
- Check for transaction management issues in the orchestrator
- Verify correlation ID tracking across the entire flow

## Next Steps

Based on the outcome of your testing, we'll iteratively troubleshoot and fix each component until the entire saga flow works correctly. Let's proceed methodically, addressing one issue at a time.
