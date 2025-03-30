#!/bin/bash

# Docker-specific test script for Create Order Saga

echo "Create Order Saga Orchestrator Docker Test Script"
echo ""

# Start a new saga
echo "Starting a new saga..."
RESPONSE=$(curl -s -X POST http://localhost:3000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_123",
    "order_details": {
      "foodItems": [
        {
          "name": "Burger",
          "price": 12.99,
          "quantity": 1
        }
      ],
      "deliveryLocation": "North Campus"
    }
  }')

# Extract saga ID
SAGA_ID=$(echo $RESPONSE | grep -o '"saga_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$SAGA_ID" ]; then
    echo "Failed to start saga. Response: $RESPONSE"
    exit 1
fi

echo "Started saga with ID: $SAGA_ID"

# Generate a test order ID
ORDER_ID="order-$(date +%s)"
echo "Using test order ID: $ORDER_ID"

echo "-----------------------------------------"
echo "Simulating service events..."

# Set bootstrap servers for Kafka - inside Docker container
KAFKA_SERVERS=kafka:9092

# Simulate service events
echo "1. Simulating Order Service - order.created event"
python /app/kafka_test_producer.py --bootstrap-servers $KAFKA_SERVERS --event order.created --correlation-id $SAGA_ID --order-id $ORDER_ID
sleep 2

echo "2. Simulating User Service - user.payment_info_retrieved event"
python /app/kafka_test_producer.py --bootstrap-servers $KAFKA_SERVERS --event user.payment_info_retrieved --correlation-id $SAGA_ID
sleep 2

echo "3. Simulating Payment Service - payment.authorized event"
python /app/kafka_test_producer.py --bootstrap-servers $KAFKA_SERVERS --event payment.authorized --correlation-id $SAGA_ID --order-id $ORDER_ID
sleep 2

echo "4. Simulating Order Service - order.status_updated event"
python /app/kafka_test_producer.py --bootstrap-servers $KAFKA_SERVERS --event order.status_updated --correlation-id $SAGA_ID --order-id $ORDER_ID
sleep 2

echo "5. Simulating Timer Service - timer.started event"
python /app/kafka_test_producer.py --bootstrap-servers $KAFKA_SERVERS --event timer.started --correlation-id $SAGA_ID --order-id $ORDER_ID
sleep 2

echo "-----------------------------------------"
echo "Checking final saga status..."

# Check final status
FINAL_STATUS=$(curl -s http://localhost:3000/api/sagas/$SAGA_ID)
echo "Saga final status: $FINAL_STATUS"

# Check if saga completed successfully
if echo $FINAL_STATUS | grep -q '"status":"COMPLETED"'; then
    echo "✅ Test completed successfully. Saga has been completed."
    exit 0
else
    echo "❌ Test failed. Saga did not complete successfully."
    exit 1
fi
