# Payment Service Testing Guide for Beginners

This guide provides simple, step-by-step instructions for testing the Payment Service. You don't need to be an expert programmer to follow along!

## What We're Testing

We'll be testing two main connections:
1. **Kafka Integration**: How our payment service communicates with other services
2. **Stripe Integration**: How our payment service processes payments

## Prerequisites (Things You Need Before Starting)

1. **Docker and Docker Compose**: These tools allow you to run the services on your computer
   - If not installed, download from [Docker's website](https://www.docker.com/products/docker-desktop)

2. **Stripe Test Account**: This is for testing payments without using real money
   - Create a free account at [Stripe's website](https://dashboard.stripe.com/register)
   - Get your test API keys from the Stripe Dashboard
   - Add these keys to your `.env` file:
     ```
     STRIPE_SECRET_KEY=sk_test_your_key_here
     STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
     STRIPE_WEBHOOK_SECRET=whsec_your_key_here
     ```

3. **Test Stripe Customer ID**: We use `cus_S2oxjQYZK8Z1Qy` in our examples
   - You can create your own test customer in the Stripe Dashboard if needed

## Step 1: Start the Services

First, we need to start all the required services. This is like turning on all the pieces of our application.

```bash
docker-compose up -d payment-db payment-service create-order-saga-db create-order-saga-orchestrator kafka zookeeper
```

**What this does**: Starts the database, payment service, messaging system (Kafka), and other required components.

**Wait about 30 seconds** for everything to start up. You can check if the payment service is ready by looking at its logs:

```bash
docker-compose logs -f payment-service
```

Look for messages that say the service has started successfully. Press `Ctrl+C` to exit the logs when you're done.

## Step 2: Test Basic Communication

Now we'll test if our payment service can receive messages and process them correctly.

### 2.1 Create a Test Message

We'll create a file with a test payment request:

```bash
# Copy and paste this ENTIRE command - it creates a file with our test payment message
echo "{\"type\":\"authorize_payment\",\"correlation_id\":\"test-123\",\"timestamp\":\"2025-03-31T10:30:00Z\",\"payload\":{\"order_id\":\"test-order-987\",\"customer\":{\"clerkUserId\":\"clerk_test_user_id\",\"stripeCustomerId\":\"cus_S2oxjQYZK8Z1Qy\",\"userStripeCard\":{\"payment_method_id\":\"pm_card_visa\"}},\"order\":{\"amount\":1299,\"description\":\"Direct test payment\"},\"return_url\":\"http://localhost:3000/checkout/complete\"}}" > payment_test_message.json
```

**What this does**: Creates a file called `payment_test_message.json` that contains a sample payment request. Think of this as a fake order for $12.99.

> **TIP**: If you're on Windows and having issues with the command, you can also create this file manually in a text editor and save it as `payment_test_message.json`.

### 2.2 Send the Test Message

Now we'll send this test message to our payment service through Kafka:

```bash
cat payment_test_message.json | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands
```

**What this does**: Takes our test message and sends it to the "payment_commands" channel where our payment service is listening.

### 2.3 Check the Payment Service Response

Let's see how our payment service handled the message:

```bash
docker logs campusg-payment-service-1 --tail 50
```

**What to look for**: You should see messages that show:
- The service received our command
- It created or updated a payment record
- It contacted Stripe to create a payment
- It published a success message back

Look for lines similar to:
```
Received command authorize_payment from payment_commands with correlation_id test-123
Handling authorize_payment command for correlation_id: test-123
Payment record [some-id] created/updated for order test-order-987 status: INITIATING
Attempting to create Stripe PaymentIntent...
Stripe PaymentIntent [some-id] created for order test-order-987 status: requires_capture
Publishing event payment.authorized to payment_events with correlation_id test-123
```

If you see these messages, your payment service is working correctly! 🎉

## Step 3: Check for Response Messages

Let's verify that our payment service actually sent back a response message:

```bash
docker exec -it campusg-kafka-1 kafka-console-consumer --bootstrap-server kafka:9092 --topic payment_events --from-beginning
```

**What this does**: Shows all messages on the "payment_events" channel, which is where our payment service reports the results of payment operations.

**What to look for**: You should see a JSON message that looks something like:
```json
{"type":"payment.authorized","correlation_id":"test-123","timestamp":"2025-03-31T14:32:06.047Z","payload":{"payment_id":"bcaab9da-c3f0-45ec-be90-9707d773780b","order_id":"test-order-987","payment_intent_id":"pi_3R8jNhC6VpJLnLai0XYnOQSf","status":"AUTHORIZED"},"source":"payment-service"}
```

This message tells other services that the payment was successfully authorized.

Press `Ctrl+C` to exit when you're done looking at the messages.

## Step 4: Verify in Stripe Dashboard

Now let's check if the payment actually appeared in Stripe:

1. Open your web browser and go to [Stripe Dashboard](https://dashboard.stripe.com/test/payments)
2. Log in if needed
3. Look for a new payment with:
   - Amount: $12.99
   - Status: "Requires capture"
   - Description: "Direct test payment"

If you see this payment, it means our payment service successfully communicated with Stripe! 🎉

## Step 5: Test the Complete Flow (Optional)

If you want to test how the payment service works with the entire order process, you can run the full integration test:

```bash
# First, copy the test scripts into the container
docker cp services/create-order-saga-orchestrator/fixed_kafka_test_producer.py campusg-create-order-saga-orchestrator-1:/app/
docker cp services/create-order-saga-orchestrator/test_payment_integration.py campusg-create-order-saga-orchestrator-1:/app/

# Then run the integration test
docker exec -it campusg-create-order-saga-orchestrator-1 python /app/test_payment_integration.py
```

This will simulate a complete order flow including the payment process.

## Troubleshooting Guide

If something didn't work as expected, here are some common issues and how to fix them:

### Error: "Payment service didn't respond"

**Possible causes and solutions:**
- **Services not fully started**: Wait a bit longer and try again
- **Kafka not running**: Restart the Kafka service with `docker-compose restart kafka`
- **Payment service crashed**: Check the logs with `docker logs campusg-payment-service-1` for error messages

### Error: "Invalid JSON format"

**Possible causes and solutions:**
- **Message file has errors**: Double-check the payment_test_message.json file
- **Special characters issue**: Try creating the file manually in a text editor instead of using echo
- **Try the fixed version**: We've included a pre-made file you can use: `payment_test_message_fixed.json`

### Error: "Stripe API key invalid"

**Possible causes and solutions:**
- **Missing or wrong API key**: Check your `.env` file for the correct Stripe test API keys
- **Using production keys**: Make sure you're using test mode keys (they start with `sk_test_`)
- **Restart after key change**: Run `docker-compose restart payment-service` after fixing the keys

### Error: "Database table not found"

**Possible causes and solutions:**
- **Database needs reset**: Run this command to reset the database:
  ```bash
  docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "DROP TABLE IF EXISTS payments CASCADE;"
  docker restart campusg-payment-service-1
  ```

### Error: "Stripe customer ID not found"

**Possible causes and solutions:**
- **Using invalid customer ID**: Try using our test ID: `cus_S2oxjQYZK8Z1Qy`
- **Create your own customer**: In the Stripe Dashboard, create a test customer and use that ID
- **Edit the test message**: Update the `stripeCustomerId` field in the test message

## Useful Commands for Debugging

Here are some helpful commands for checking what's happening:

- **Check Payment Service Logs**:
  ```bash
  docker logs campusg-payment-service-1
  ```

- **See All Running Services**:
  ```bash
  docker-compose ps
  ```

- **Restart a Service**:
  ```bash
  docker-compose restart payment-service
  ```

- **Check Kafka Topics**:
  ```bash
  docker exec campusg-kafka-1 kafka-topics --list --bootstrap-server kafka:9092
  ```

## Glossary of Terms

- **Kafka**: A messaging system that lets different services communicate
- **Payment Intent**: Stripe's way of tracking a payment from start to finish
- **Webhook**: A way for Stripe to notify our service about payment events
- **Saga**: A pattern for managing transactions across multiple services
- **Container**: An isolated environment where a service runs
- **JSON**: A format for structuring data that's easy for computers to process

Congratulations! You've successfully tested the payment service. If you have any questions or encounter issues not covered in this guide, please reach out to the development team.
