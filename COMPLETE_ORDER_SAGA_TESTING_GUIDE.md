# Complete Order Saga Testing Guide

This guide will help you set up and test the Complete Order Saga, which handles the process of completing a food delivery order when a runner marks it as delivered.

## Overview

The Complete Order Saga orchestrates the following steps:
1. Update order status to DELIVERED
2. Retrieve runner's payment information
3. Release funds to the runner
4. Update order status to COMPLETED

## Recent Changes

The following changes have been made to fix issues in the Complete Order Saga implementation:

1. **Fixed duplicate handler methods** in the saga orchestrator
2. **Fixed parameter mismatches** in command publishing
3. **Added database migration support** with initial migration script
4. **Added a temporary stub** for the release funds functionality in the payment service
5. **Added automated test script** for testing the saga flow
6. **Updated Docker setup** to run migrations automatically

## Setting Up and Testing

### 1. Start Required Services

```bash
# Navigate to the project root
cd /path/to/campusG

# Bring up all the services
docker-compose up -d
```

If you only want to test the Complete Order Saga, you can start just the required services:

```bash
docker-compose up -d postgres kafka zookeeper order-service payment-service user-service complete-order-saga-orchestrator
```

### 2. Create a Test Order

If you need a test order to use with the saga:

```bash
# Access the order-service container
docker-compose exec order-service bash

# Inside the container, use the Flask shell to create a test order
flask shell

# In the Flask shell, create an order
from app.models import Order
from app import db
import uuid

order = Order(
    id=str(uuid.uuid4()),
    user_id="test-user",
    restaurant_id="test-restaurant",
    status="ACCEPTED",
    total_amount=25.00
)
db.session.add(order)
db.session.commit()
print(f"Created test order with ID: {order.id}")

# Exit the Flask shell
exit()

# Exit the container
exit
```

### 3. Run the Test Script

The simplest way to test the Complete Order Saga is to use the provided test script:

```bash
# From the project root, run the test script with your order ID
python services/complete-order-saga-orchestrator/test_complete_order.py your-order-id-here

# If you don't provide an order ID, the script will generate a random one
python services/complete-order-saga-orchestrator/test_complete_order.py
```

The test script will:
1. Trigger the saga for the specified order
2. Monitor the saga state via the SSE endpoint
3. Report success or failure

### 4. Manual Testing

If you prefer to test manually:

1. **Trigger the saga**:
   ```bash
   curl -X POST http://localhost:3000/saga/complete/completeOrder \
     -H "Content-Type: application/json" \
     -d '{"orderId": "your-order-id-here"}'
   ```
   You'll receive a response with the saga ID:
   ```json
   {
     "message": "Complete order saga started successfully",
     "orderId": "your-order-id-here",
     "sagaId": "generated-saga-id",
     "status": "STARTED",
     "timestamp": "..."
   }
   ```

2. **Monitor the saga state**:
   ```bash
   # Use the saga ID from the previous response
   curl -N http://localhost:3000/saga/complete/orderUpdateStream/saga-id-here
   ```
   This will stream state updates as they occur.

### 5. Monitoring Kafka Messages

To see what's happening behind the scenes:

```bash
# In one terminal, monitor command messages
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic complete_order_commands --from-beginning

# In another terminal, monitor event messages
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic complete_order_events --from-beginning
```

### 6. Checking Service Logs

To see detailed logs from each service:

```bash
# View complete-order-saga-orchestrator logs
docker-compose logs -f complete-order-saga-orchestrator

# View payment-service logs
docker-compose logs -f payment-service

# View order-service logs
docker-compose logs -f order-service
```

## Understanding the Current Implementation

The current implementation includes a temporary stub for the "release funds" functionality in the payment service. This stub always returns a successful `funds_released` event to allow testing of the complete saga flow.

When a "release_funds" command is received:
1. The stub logs the command details
2. Updates the payment status to RELEASED if the payment exists in the database
3. Always returns a successful funds_released event

This allows you to test the end-to-end saga flow while the actual payment processing implementation is being developed in a separate branch.

## Troubleshooting

### Database Issues

If you encounter database issues:

1. **Check if the saga database exists**:
   ```bash
   docker-compose exec postgres psql -U postgres -c "\l" | grep complete_order_saga_db
   ```

2. **Create the database if it doesn't exist**:
   ```bash
   docker-compose exec postgres psql -U postgres -c "CREATE DATABASE complete_order_saga_db;"
   ```

3. **Check if tables are created**:
   ```bash
   docker-compose exec postgres psql -U postgres -d complete_order_saga_db -c "\dt"
   ```

4. **Run migrations manually if needed**:
   ```bash
   docker-compose exec complete-order-saga-orchestrator flask db upgrade
   ```

### Kafka Issues

If Kafka-related issues occur:

1. **Check if Kafka is running**:
   ```bash
   docker-compose ps kafka zookeeper
   ```

2. **Verify topics exist**:
   ```bash
   docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
   ```

3. **Create missing topics**:
   ```bash
   docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic complete_order_commands --partitions 1 --replication-factor 1
   docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic complete_order_events --partitions 1 --replication-factor 1
   ```

## Next Steps

After verifying that the saga flow works correctly with the temporary stub, you can implement the actual fund release functionality in the payment service.
