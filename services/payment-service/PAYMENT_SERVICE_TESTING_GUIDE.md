# Payment Service Testing Guide

This guide provides simple, step-by-step instructions for testing the Payment Service with a focus on verifying database updates.

## What We're Testing

We'll be testing two main aspects:
1. **Database Schema**: Checking that the database is using the updated payment status values
2. **Payment Flow**: Verifying the payment flow from authorization to completion

## Prerequisites

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

3. **Test User Details**: We have two test users available:
   
   **Customer (for payment authorization):**
   ```
   Stripe Customer ID: cus_S4gg5SQhl4R6jC
   ```
   
   **Runner (for payment release):**
   ```
   Runner ID: user_2ulBCA0zGBude9I8dgintjlGWyD
   Connect Account ID: acct_1RAXKc4EjkIzXfSa
   ```

## Start the Services

First, start all the required services:

```bash
docker compose up -d payment-db payment-service kafka zookeeper
```

Wait about 30 seconds for everything to start up.

## Basic Flow: Verify Database Schema and Payment Status Updates

### 1. Verify the Database Schema

```bash
# Connect to the payment database and check the enum type
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "\dT+"
```

Verify that the `payment_status_enum` shows the updated values:
- AUTHORIZED
- SUCCEEDED
- REVERTED
- FAILED

### 2. Test Payment Authorization

```bash
# Send a test authorization command (one line)
echo "{\"type\":\"authorize_payment\",\"correlation_id\":\"test-auth-123\",\"payload\":{\"order_id\":\"test-order-123\",\"customer\":{\"clerkUserId\":\"user_2uFnauOsxFRGIoy3O5CJA6v5sM6\",\"stripeCustomerId\":\"cus_S4gg5SQhl4R6jC\",\"userStripeCard\":{\"payment_method_id\":\"pm_card_visa\"}},\"order\":{\"amount\":1599,\"description\":\"Test order\"},\"return_url\":\"http://localhost:3000/checkout/complete\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands
```

### 3. Check Database Status After Authorization

```bash
# Check the payment record status
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "SELECT payment_id, order_id, status FROM payments ORDER BY created_at DESC LIMIT 1;"
```

Verify the status is `AUTHORIZED` and save the payment_id for the next step.

### 4. Test Payment Release

```bash
# Send a payment release command (replace PAYMENT_ID with your actual payment ID from step 3)
echo "{\"type\":\"release_payment\",\"correlation_id\":\"test-release-123\",\"payload\":{\"payment_id\":\"PAYMENT_ID\",\"runner_id\":\"user_2ulBCA0zGBude9I8dgintjlGWyD\",\"runner_connect_account_id\":\"acct_1RAXKc4EjkIzXfSa\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands
```

### 5. Check Database Status After Release

```bash
# Check the final payment status
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "SELECT order_id, status FROM payments ORDER BY created_at DESC LIMIT 1;"
```

Verify the status is now `SUCCEEDED`.

## Additional Testing Examples

### Example 1: Testing Multiple Orders

Test handling multiple orders with one-liner commands:

```bash
# Order 1: Standard meal order
echo "{\"type\":\"authorize_payment\",\"correlation_id\":\"test-multi-1\",\"payload\":{\"order_id\":\"multi-order-1\",\"customer\":{\"clerkUserId\":\"user_2uFnauOsxFRGIoy3O5CJA6v5sM6\",\"stripeCustomerId\":\"cus_S4gg5SQhl4R6jC\",\"userStripeCard\":{\"payment_method_id\":\"pm_card_visa\"}},\"order\":{\"amount\":1299,\"description\":\"Chicken Rice Meal\"},\"return_url\":\"http://localhost:3000/checkout/complete\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands

# Order 2: Larger order
echo "{\"type\":\"authorize_payment\",\"correlation_id\":\"test-multi-2\",\"payload\":{\"order_id\":\"multi-order-2\",\"customer\":{\"clerkUserId\":\"user_2uFnauOsxFRGIoy3O5CJA6v5sM6\",\"stripeCustomerId\":\"cus_S4gg5SQhl4R6jC\",\"userStripeCard\":{\"payment_method_id\":\"pm_card_visa\"}},\"order\":{\"amount\":2599,\"description\":\"Family Meal Bundle\"},\"return_url\":\"http://localhost:3000/checkout/complete\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands

# Order 3: Small order
echo "{\"type\":\"authorize_payment\",\"correlation_id\":\"test-multi-3\",\"payload\":{\"order_id\":\"multi-order-3\",\"customer\":{\"clerkUserId\":\"user_2uFnauOsxFRGIoy3O5CJA6v5sM6\",\"stripeCustomerId\":\"cus_S4gg5SQhl4R6jC\",\"userStripeCard\":{\"payment_method_id\":\"pm_card_visa\"}},\"order\":{\"amount\":499,\"description\":\"Beverage Only\"},\"return_url\":\"http://localhost:3000/checkout/complete\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands
```

Check all payments are created in the database:
```bash
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "SELECT order_id, amount, status FROM payments WHERE order_id LIKE 'multi-order-%';"
```

To release payments for these orders, get each payment ID and send release commands:

```bash
# Get payment IDs
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "SELECT payment_id, order_id FROM payments WHERE order_id LIKE 'multi-order-%';"

# Then for each payment ID, send a release command (replace PAYMENT_ID accordingly)
echo "{\"type\":\"release_payment\",\"correlation_id\":\"release-multi-1\",\"payload\":{\"payment_id\":\"PAYMENT_ID\",\"runner_id\":\"user_2ulBCA0zGBude9I8dgintjlGWyD\",\"runner_connect_account_id\":\"acct_1RAXKc4EjkIzXfSa\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands
```



echo "{\"type\":\"release_payment\",\"correlation_id\":\"release-multi-1\",\"payload\":{\"payment_id\":\"e0e8027a-504a-4a66-9ea0-1514a451b03e\",\"runner_id\":\"user_2ulBCA0zGBude9I8dgintjlGWyD\",\"runner_connect_account_id\":\"acct_1RAXKc4EjkIzXfSa\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands

### Example 2: Testing a Failed Payment

Test how the system handles payment failures by using an invalid payment method:

```bash
# Use a payment method that will be declined
echo "{\"type\":\"authorize_payment\",\"correlation_id\":\"test-fail-1\",\"payload\":{\"order_id\":\"fail-order-1\",\"customer\":{\"clerkUserId\":\"user_2uFnauOsxFRGIoy3O5CJA6v5sM6\",\"stripeCustomerId\":\"cus_S4gg5SQhl4R6jC\",\"userStripeCard\":{\"payment_method_id\":\"pm_card_decline\"}},\"order\":{\"amount\":9999,\"description\":\"Order with declined payment\"},\"return_url\":\"http://localhost:3000/checkout/complete\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands
```

Check the database for failed payment status:
```bash
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "SELECT order_id, status FROM payments WHERE order_id = 'fail-order-1';"
```

Verify the status is `FAILED`.

### Example 3: Testing Payment Reversal

Test the payment reversal flow (refund):

```bash
# 1. First authorize a payment
echo "{\"type\":\"authorize_payment\",\"correlation_id\":\"test-revert-1\",\"payload\":{\"order_id\":\"revert-order-1\",\"customer\":{\"clerkUserId\":\"user_2uFnauOsxFRGIoy3O5CJA6v5sM6\",\"stripeCustomerId\":\"cus_S4gg5SQhl4R6jC\",\"userStripeCard\":{\"payment_method_id\":\"pm_card_visa\"}},\"order\":{\"amount\":1999,\"description\":\"Order to be reverted\"},\"return_url\":\"http://localhost:3000/checkout/complete\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands

# 2. Get the payment ID
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "SELECT payment_id FROM payments WHERE order_id = 'revert-order-1';"

389f00ec-5d21-40b3-903a-74d7db08ae2a

echo "{\"type\":\"revert_payment\",\"correlation_id\":\"test-revert-1\",\"payload\":{\"payment_id\":\"389f00ec-5d21-40b3-903a-74d7db08ae2a\",\"reason\":\"Customer canceled order\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands

# 3. Send a revert payment command (replace PAYMENT_ID with the actual ID)
echo "{\"type\":\"revert_payment\",\"correlation_id\":\"test-revert-1\",\"payload\":{\"payment_id\":\"PAYMENT_ID\",\"reason\":\"Customer canceled order\"}}" | docker exec -i campusg-kafka-1 kafka-console-producer --bootstrap-server kafka:9092 --topic payment_commands

# 4. Check the database for reverted payment status
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "SELECT order_id, status FROM payments WHERE order_id = 'revert-order-1';"
```

Verify the status is `REVERTED`.

## Troubleshooting Guide

### Common Database Issues

#### Issue: Old Enum Values Still Present

If you see the old values (INITIATING, RELEASED) in the database enum type:

```bash
# Connect to the database and check the enum type
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "\dT+"
```

Solution: Reset the database and recreate it with the new schema:

```bash
# Stop the payment service
docker compose stop payment-service

# Remove the payment database volume
docker volume rm campusg_payment-db-data

# Restart the services
docker compose up -d payment-db payment-service
```

#### Issue: Database Connection Errors

If the payment service can't connect to the database:

```bash
# Check if the database is running
docker compose ps payment-db

# If needed, restart the database
docker compose restart payment-db

# Wait 10-15 seconds, then restart the payment service
docker compose restart payment-service
```

### JSON Message Issues

If your JSON messages cause errors, make sure:

1. All quotes are properly escaped with backslashes in the echo command
2. The JSON is valid and properly formatted
3. Try sending the message as a single line without line breaks

## Checking Logs

To understand what's happening in the payment service:

```bash
docker logs campusg-payment-service-1 --tail 50
```

Look for:
- Payment status changes (AUTHORIZED → SUCCEEDED)
- Stripe API interactions
- Any error messages

## Useful Commands

- **Check Payment Service Logs**:
  ```bash
  docker logs campusg-payment-service-1
  ```

- **Restart a Service**:
  ```bash
  docker compose restart payment-service
  ```

- **Check Kafka Topics**:
  ```bash
  docker exec campusg-kafka-1 kafka-topics --list --bootstrap-server kafka:9092
  ```

- **Reset the Database**:
  ```bash
  docker compose down -v payment-db
  docker compose up -d payment-db payment-service
  ```

Congratulations! You've successfully tested the payment service and verified the database updates properly. If you have any questions, please reach out to the development team.
