# User Service Kafka Integration Testing Guide

This guide provides step-by-step instructions to verify that the User Service is correctly integrated with Kafka for payment processing, specifically for the flow:

```
User Service → Kafka (user_events) → Create Order Saga → Kafka (payment_commands) → Payment Service → Stripe
```

## Prerequisites

- Docker and Docker Compose installed
- The project repository cloned and navigated to the project root
- Docker Compose services running (`docker-compose up -d`)

## Testing Steps

### 1. Test User Creation with Stripe Customer ID

First, let's verify that new users are created with a Stripe Customer ID:

```bash
# Simulate a Clerk webhook event to create a new test user
curl -X POST http://localhost:3001/api/webhook/clerk \
-H "Content-Type: application/json" \
-d '{
  "type": "user.created",
  "object": "event",
  "data": {
    "id": "user_test_kafka_1",
    "first_name": "Kafka",
    "last_name": "Test",
    "email_addresses": [
      {
        "id": "idn_test_kafka_1",
        "email_address": "kafka.test.1@example.com"
      }
    ],
    "phone_numbers": [],
    "username": "kafkatest1",
    "created_at": 1678886400000,
    "updated_at": 1678886400000
  }
}'
```

Check the User Service logs to confirm successful user and Stripe customer creation:

```bash
docker-compose logs user-service | grep "Created Stripe customer"
```

You should see output like:
```
user-service-1  | 2025-04-01 XX:XX:XX,XXX - app - INFO - Created Stripe customer cus_XXXXXXXXXX for user user_test_kafka_1
```

### 2. Test Kafka Command Reception and Response

Now let's test that the User Service receives commands from Kafka and publishes responses:

#### Step 1: Start a Kafka consumer to watch for responses

In a separate terminal, run:

```bash
docker-compose exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic user_events --from-beginning
```

Keep this terminal open to see incoming messages.

#### Step 2: Send a test message to the User Service

In a new terminal, run:

```bash
# Generate a unique correlation ID (replace with your own or use as is)
CORRELATION_ID="test_kafka_$(date +%s)"

# Send a message to user_commands topic
docker-compose exec kafka kafka-console-producer --bootstrap-server kafka:9092 --topic user_commands << EOF
{"type": "get_user_payment_info", "correlation_id": "${CORRELATION_ID}", "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")", "payload": {"clerkUserId": "user_test_kafka_1", "order": {"amount": 5000, "description": "Test Order for Kafka Integration"}}}
EOF
```

#### Step 3: Observe the response

In the first terminal where the consumer is running, you should see a response message like:

```json
{"type": "user.payment_info_failed", "correlation_id": "test_kafka_XXXXXXXXX", "timestamp": "2025-04-01TXX:XX:XX.XXXXXX+00:00", "payload": {"error": "Default payment method not set for user"}, "source": "user-service"}
```

Note: The error about the missing payment method is expected since we haven't added one to our test user.

#### Step 4: Check User Service logs

You can also check the User Service logs to confirm the message was received and processed:

```bash
docker-compose logs user-service | grep "${CORRELATION_ID}"
```

You should see logs indicating:
1. Receipt of the message with your correlation ID
2. Processing of the message
3. Publishing of the response

### 3. (Optional) Test Complete Flow with Payment Method

To test the success path (requires Stripe API key configuration):

#### Step 1: Add a payment method to the test user

```bash
curl -X PUT http://localhost:3001/api/user/user_test_kafka_1/payment \
-H "Content-Type: application/json" \
-d '{
  "paymentMethodId": "pm_card_visa"
}'
```

#### Step 2: Repeat the Kafka test above

Now when you send the same Kafka message and observe the response, you should see a successful response:

```json
{"type": "user.payment_info_retrieved", "correlation_id": "test_kafka_XXXXXXXXX", "timestamp": "2025-04-01TXX:XX:XX.XXXXXX+00:00", "payload": {"customer": {"clerkUserId": "user_test_kafka_1", "stripeCustomerId": "cus_XXXXXXXXXX", "userStripeCard": {"payment_method_id": "pm_card_visa", "last4": "4242", "brand": "visa", ...}}, "order": {"amount": 5000, "description": "Test Order for Kafka Integration"}}, "source": "user-service"}
```

## Verification Checklist

✅ **User Creation:** The User Service creates a Stripe Customer ID for new users.

✅ **Kafka Reception:** The User Service receives messages from the `user_commands` topic.

✅ **Kafka Publication:** The User Service publishes responses to the `user_events` topic.

✅ **Message Format:** The response messages follow the format specified in PAYMENT_DATA_GUIDE.md.

✅ **Error Handling:** The User Service correctly reports issues (like missing payment methods).

These tests confirm that the User Service correctly implements its part of the payment flow.
