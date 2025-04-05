# Kafka Integration Testing Guide

This document provides a simple, step-by-step guide for testing the Kafka integration in the CampusG system. Follow these instructions to verify that all components are properly communicating through Kafka topics.

## Prerequisites

- Docker and Docker Compose installed
- Project repository cloned

## Quick Start Testing Guide

### 1. Start the System

```bash
# Start all services
docker-compose up -d

# Wait for services to be healthy (about 2-3 minutes)
docker-compose ps
```

### 2. Verify Kafka Topics

```bash
# List all Kafka topics to verify naming convention
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

You should see these topics with underscore naming:
- `order_events`
- `payment_events`
- `user_events`
- `timer_events`
- `notification_events`
- `order_commands`
- `payment_commands`
- `user_commands`
- `timer_commands`
- `escrow_events`

### 3. Run the Comprehensive Test

This test simulates the entire order creation and cancellation flows:

```bash
# Navigate to the saga orchestrator directory
cd services/create-order-saga-orchestrator

# Run the comprehensive test
python comprehensive_test.py --docker
```

The test should complete with these success messages:
- "🎉 Create Order Saga Test Flow completed successfully!"
- "🎉 Order Cancellation Test Flow completed successfully!"
- "All tests completed successfully!"

### 4. Verify Notifications Were Captured

Check that notifications were captured from all topics:

```bash
# See counts of notifications by topic source
docker-compose exec notification-db psql -U postgres -d notification_db -c "SELECT source_topic, COUNT(*) FROM notifications GROUP BY source_topic ORDER BY COUNT(*) DESC;"
```

You should see counts for the underscore-formatted topics like `order_events`, `payment_events`, etc.

### 5. Test Real Order Flow (Manual Testing)

To manually test a real order flow:

1. Create a new order:
```bash
curl -X POST http://localhost:3101/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_test123",
    "order_details": {
      "foodItems": [
        {
          "name": "Test Burger",
          "price": 15.99,
          "quantity": 1
        }
      ],
      "deliveryLocation": "Test Location"
    }
  }'
```

2. From the response, note the `saga_id` value

3. Check the saga status:
```bash
curl http://localhost:3101/sagas/{saga_id}
```
Replace `{saga_id}` with the actual ID from step 2

4. Check notifications in the database:
```bash
docker-compose exec notification-db psql -U postgres -d notification_db -c "SELECT created_at, source_topic, event_type, order_id FROM notifications WHERE correlation_id='{saga_id}' ORDER BY created_at ASC;"
```
Replace `{saga_id}` with the actual ID

5. Verify the saga completes:
Wait a few seconds and check again. The saga status should eventually be "COMPLETED".
```bash
curl http://localhost:3101/sagas/{saga_id}
```

## Troubleshooting

If you encounter issues:

1. Check if all services are running:
```bash
docker-compose ps
```

2. Inspect logs for specific services:
```bash
docker-compose logs -f notification-service
docker-compose logs -f create-order-saga-orchestrator
```

3. Restart problematic services:
```bash
docker-compose restart notification-service
```

4. Make sure Kafka topics are created correctly:
```bash
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

## Understanding the Flow

Here's what happens when an order is created:

1. Create Order API call → Saga Orchestrator initializes
2. Orchestrator → `order_commands` → Order Service creates order
3. Order Service → `order_events` → Orchestrator moves to next step
4. Orchestrator → `user_commands` → User Service gets payment info
5. User Service → `user_events` → Orchestrator moves to next step
6. Orchestrator → `payment_commands` → Payment Service authorizes payment
7. Payment Service → `payment_events` → Orchestrator moves to next step
8. Orchestrator → `order_commands` → Order Service updates status
9. Order Service → `order_events` → Orchestrator moves to next step
10. Orchestrator → `timer_commands` → Timer Service starts timer
11. Timer Service → `timer_events` → Orchestrator completes saga

Throughout this entire flow, the Notification Service silently captures all messages from Kafka topics and stores them in its database.
