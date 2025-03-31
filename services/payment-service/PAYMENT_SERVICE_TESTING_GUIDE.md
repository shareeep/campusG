# Payment Service Testing Guide

This guide provides step-by-step instructions for testing the Payment Service's integration with Kafka and Stripe.

## Prerequisites

1. Docker and Docker Compose installed
2. Valid Stripe test account with API keys configured in `.env`
3. A valid Stripe test customer ID (we used: `cus_S2oxjQYZK8Z1Qy` in our tests)
4. `ngrok` installed (for Stripe webhook testing)

## Step 1: Start Required Services

Start the payment service and related dependencies:

```bash
docker-compose up -d payment-db payment-service create-order-saga-db create-order-saga-orchestrator kafka zookeeper
```

Wait for all services to initialize (you can check logs with `docker-compose logs -f payment-service`).

## Step 2: Basic Communication Test

First, let's verify that the Payment Service is properly connected to Kafka:

1. Create a test message file:

```bash
echo "{\"type\":\"authorize_payment\",\"correlation_id\":\"test-123\",\"timestamp\":\"2025-03-31T10:30:00Z\",\"payload\":{\"order_id\":\"test-order-987\",\"customer\":{\"clerkUserId\":\"clerk_test_user_id\",\"stripeCustomerId\":\"YOUR_STRIPE_CUSTOMER_ID\",\"userStripeCard\":{\"payment_method_id\":\"pm_card_visa\"}},\"order\":{\"amount\":1299,\"description\":\"Direct test payment\"},\"return_url\":\"http://localhost:3000/checkout/complete\"}}" > payment_test_message.json
```

2. Send the message to the payment_commands Kafka topic:

```bash
cat payment_test_message.json | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands
```

3. Check the payment service logs:

```bash
docker logs campusg-payment-service-1 --tail 50
```

**Expected Outcome:**
```
Received command authorize_payment from payment_commands with correlation_id test-123
Handling authorize_payment command for correlation_id: test-123
Payment record [UUID] created/updated for order test-order-987 status: INITIATING
Attempting to create Stripe PaymentIntent for order test-order-987 amount 1299 cents
...
Stripe PaymentIntent [PI_ID] created for order test-order-987 status: requires_capture
Publishing event payment.authorized to payment_events with correlation_id test-123
```

## Step 3: Check Events on the Payment Events Topic

Monitor the Kafka events published by the Payment Service:

```bash
docker exec -it campusg-kafka-1 kafka-console-consumer --bootstrap-server kafka:9092 --topic payment_events --from-beginning
```

**Expected Outcome:**
You should see messages like:
```json
{"type":"payment.authorized","correlation_id":"test-123","timestamp":"2025-03-31T14:32:06.047Z","payload":{"payment_id":"bcaab9da-c3f0-45ec-be90-9707d773780b","order_id":"test-order-987","payment_intent_id":"pi_3R8jNhC6VpJLnLai0XYnOQSf","status":"AUTHORIZED"},"source":"payment-service"}
```

Press Ctrl+C to exit the consumer when done.

## Step 4: Verify in Stripe Dashboard

1. Log in to your [Stripe Dashboard](https://dashboard.stripe.com/test/payments)
2. Navigate to the Payments section
3. Verify that a new payment intent was created with:
   - Status: "Requires capture"
   - Amount: $12.99
   - Description matching your test command

## Step 5: Stripe Webhook Integration (Already Configured)

The webhook integration has already been set up with:
- ngrok running to expose the payment service
- Webhook endpoint configured in Stripe Dashboard
- Webhook secret added to the `.env` file as `STRIPE_WEBHOOK_SECRET=whsec_iSs3FoF0FuRudUQYvaTDO7fUv4BMpcWL`

The webhook system handles these Stripe events:
- `payment_intent.succeeded`: When a payment is fully processed
- `payment_intent.canceled`: When a payment is canceled
- `payment_intent.payment_failed`: When a payment fails for any reason

When these events are received from Stripe, the webhook handler in `webhook_routes.py`:
1. Verifies the webhook signature
2. Updates the payment record status in the database
3. Publishes appropriate events to Kafka for the saga orchestrator

## Step 6: Testing the Full Saga Flow

If you want to test the complete flow with the Create Order Saga, you can use the provided test script:

```bash
# Copy the test scripts to the container
docker cp services/create-order-saga-orchestrator/fixed_kafka_test_producer.py campusg-create-order-saga-orchestrator-1:/app/
docker cp services/create-order-saga-orchestrator/test_payment_integration.py campusg-create-order-saga-orchestrator-1:/app/

# Run the integration test
docker exec -it campusg-create-order-saga-orchestrator-1 python /app/test_payment_integration.py
```

## Troubleshooting

### Common Issues

1. **JSON Format Errors**: 
   - Check that your JSON message is properly formatted
   - Ensure all quotes are escaped correctly when creating test messages

2. **Stripe API Key Issues**:
   - Verify your API keys in the `.env` file
   - Make sure you're using test mode keys

3. **Database Schema Issues**:
   - If you encounter database errors, you may need to recreate the schema:
   ```bash
   docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "DROP TABLE IF EXISTS payments CASCADE;"
   docker restart campusg-payment-service-1
   ```

### Monitoring Tools

- **Payment Service Logs**: `docker logs campusg-payment-service-1`
- **Kafka Topics**: Use kafka-console-consumer to monitor topics
- **Stripe Dashboard**: Check payment intents and webhook deliveries
