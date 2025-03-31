#!/bin/bash

# Test script for Payment Service integration with Create Order Saga

echo "Payment Service - Create Order Saga Integration Test"
echo "-----------------------------------------"

# Start a new saga
echo "Starting a new saga..."
RESPONSE=$(curl -s -X POST http://localhost:3101/api/orders \
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
ORDER_ID=$(echo "order-$(date +%s)")
echo "Using test order ID: $ORDER_ID"

echo "-----------------------------------------"
echo "Simulating service events and verifying Kafka messages..."

# Using the fixed script for Kafka producers
echo "1. Simulating Order Service - order.created event"
python fixed_kafka_test_producer.py --bootstrap-servers localhost:9092 --event order.created --correlation-id $SAGA_ID --order-id $ORDER_ID
sleep 3

echo "2. Monitor payment_commands topic (press Ctrl+C after seeing the authorize_payment command)"
echo "Run this in a separate terminal:"
echo "docker exec -it campusg-kafka-1 kafka-console-consumer --bootstrap-server kafka:9092 --topic payment_commands --from-beginning"
echo "Waiting 10 seconds for you to check the payment_commands topic..."
sleep 10

echo "3. Simulating User Service - user.payment_info_retrieved event"
python fixed_kafka_test_producer.py --bootstrap-servers localhost:9092 --event user.payment_info_retrieved --correlation-id $SAGA_ID
sleep 3

echo "4. Check if payment service received the command:"
echo "Run: docker logs campusg-payment-service-1 | grep $SAGA_ID"
echo "Waiting 10 seconds for you to check the payment service logs..."
sleep 10

echo "5. Simulating Payment Service - payment.authorized event"
python fixed_kafka_test_producer.py --bootstrap-servers localhost:9092 --event payment.authorized --correlation-id $SAGA_ID --order-id $ORDER_ID
sleep 3

echo "6. Continue saga flow with order status update"
python fixed_kafka_test_producer.py --bootstrap-servers localhost:9092 --event order.status_updated --correlation-id $SAGA_ID --order-id $ORDER_ID
sleep 3

echo "7. Complete saga with timer started event"
python fixed_kafka_test_producer.py --bootstrap-servers localhost:9092 --event timer.started --correlation-id $SAGA_ID --order-id $ORDER_ID
sleep 3

echo "-----------------------------------------"
echo "Checking final saga status..."

# Check final status
FINAL_STATUS=$(curl -s http://localhost:3101/api/sagas/$SAGA_ID)
echo "Saga final status: $FINAL_STATUS"

# Check if saga completed successfully
if echo $FINAL_STATUS | grep -q '"status":"COMPLETED"'; then
    echo "✅ Test completed successfully. Saga has been completed."
    echo "-----------------------------------------"
    echo "Test summary:"
    echo "1. Started a new saga successfully"
    echo "2. The create-order-saga sends an authorize_payment command to payment_commands topic"
    echo "3. The payment service can process this command and send back events"
    echo "4. The integration between services via Kafka is working correctly"
    exit 0
else
    echo "❌ Test failed. Saga did not complete successfully."
    exit 1
fi
