# CampusG Payment Service Guide

## Table of Contents

1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Setting Up the Service](#setting-up-the-service)
4. [Database Integration](#database-integration)
5. [API Endpoints](#api-endpoints)
6. [Testing Guide](#testing-guide)
7. [Integration with Other Services](#integration-with-other-services)
8. [Stripe Integration](#stripe-integration)
9. [Troubleshooting](#troubleshooting)

## Introduction

The CampusG Payment Service handles all payment processing for the CampusG platform, including:

- **Payment authorization**: Creating payment intents with Stripe
- **Escrow functionality**: Holding payments until order completion
- **Fund release**: Releasing payments to runners upon successful delivery
- **Payment reversal**: Refunding customers when orders are canceled
- **Webhook processing**: Handling asynchronous Stripe events

The service follows a microservice architecture and integrates with the User Service for customer payment details and the Order Service for order information.

## System Requirements

- Docker and Docker Compose
- Stripe account with API keys
- PostgreSQL (provided by Docker Compose)
- Python 3.11+ (for local development outside Docker)

## Setting Up the Service

### Environment Variables

Create or edit the `.env` file in the project root with the following variables:

```
# Stripe configuration
STRIPE_API_KEY=sk_test_your_test_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Service URLs (when running locally outside Docker)
USER_SERVICE_URL=http://localhost:3001
ORDER_SERVICE_URL=http://localhost:3002
```

### Starting the Service

#### Using Docker Compose (Recommended)

```bash
# From the project root directory
cd c:\whereYouStoreProject\campusG

# Start the payment service and its database
docker-compose up payment-db -d
docker-compose up payment-service -d

# Check if the service is running
docker-compose ps payment-service
```

The payment service should be running on port 3003.

### Configuring Stripe Webhooks

1. Sign in to your Stripe Dashboard
2. Navigate to Developers > Webhooks
3. Add an endpoint with the URL: `http://your-domain/api/stripe-webhook`
4. Subscribe to the following events:
   - `payment_intent.succeeded`
   - `payment_intent.canceled`
   - `payment_intent.payment_failed`
5. Copy the signing secret to your `.env` file

## Database Integration

The payment service uses a PostgreSQL database to store payment records. When running with Docker Compose, this is automatically set up using the `payment-db` service.

### Database Schema

The main entity in the database is the `Payment` model with the following structure:

| Field | Type | Description |
|-------|------|-------------|
| id | String | Primary key, UUID format |
| payment_intent_id | String | Stripe payment intent ID |
| order_id | String | Associated order ID |
| customer_id | String | Customer who made the payment |
| runner_id | String | Runner to receive the payment (when completed) |
| amount | Decimal | Payment amount in USD |
| status | Enum | Payment status (INITIATING, AUTHORIZED, RELEASED, REVERTED, FAILED) |
| description | String | Payment description |
| created_at | DateTime | Timestamp when record was created |
| updated_at | DateTime | Timestamp when record was last updated |

### Manual Database Initialization

If you need to manually initialize the database:

```bash
# Connect to the database container
docker-compose exec payment-db psql -U postgres -d payment_db

# Inside the PostgreSQL shell, create the enum type if needed
CREATE TYPE payment_status AS ENUM ('INITIATING', 'AUTHORIZED', 'RELEASED', 'REVERTED', 'FAILED');

# Create the payments table if needed
CREATE TABLE payments (
    id VARCHAR(36) PRIMARY KEY,
    payment_id VARCHAR(36) UNIQUE,
    payment_intent_id VARCHAR(255),
    order_id VARCHAR(36) NOT NULL,
    customer_id VARCHAR(36) NOT NULL,
    runner_id VARCHAR(36),
    amount NUMERIC(5,2) NOT NULL,
    status payment_status NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

# Create indexes
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_customer_id ON payments(customer_id);
CREATE INDEX idx_payments_status ON payments(status);
```

## API Endpoints

### 1. Authorize Payment

Authorizes a payment from a customer and holds it in escrow until the order is completed.

**Endpoint:** `POST /api/payment/{order_id}/authorize`

**Request Body:**
```json
{
  "customer": {
    "clerkUserId": "user_2uFnauOsxFRGIoy3O5CJA6v5sM6",
    "userStripeCard": {
      "payment_method_id": "pm_1R7xF8QR8BO665MwbdEmL3Pz"
    }
  },
  "custpaymentId": "optional_custom_payment_id"
}
```

**Sample Request (cURL):**
```bash
curl -X POST http://localhost:3003/api/payment/order_123abc/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {
      "clerkUserId": "user_2uFnauOsxFRGIoy3O5CJA6v5sM6",
      "userStripeCard": {
        "payment_method_id": "pm_1R7xF8QR8BO665MwbdEmL3Pz"
      }
    }
  }'
```

**Successful Response (200 OK):**
```json
{
  "success": true,
  "description": "Payment authorized successfully and held in escrow",
  "paymentId": "payment_abc123",
  "paymentIntentId": "pi_abc123",
  "status": "AUTHORIZED"
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "description": "Missing customer data",
  "error": "invalid_request"
}
```

### 2. Release Payment

Releases the payment from escrow to the runner when an order is successfully completed.

**Endpoint:** `POST /api/payment/{order_id}/release`

**Request Body:**
```json
{
  "runnerId": "user_abc123"
}
```

**Sample Request (cURL):**
```bash
curl -X POST http://localhost:3003/api/payment/order_123abc/release \
  -H "Content-Type: application/json" \
  -d '{
    "runnerId": "user_abc123"
  }'
```

**Successful Response (200 OK):**
```json
{
  "success": true,
  "description": "Funds released to runner successfully",
  "status": "RELEASED",
  "runnerId": "user_abc123"
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "description": "Payment cannot be released in status: FAILED",
  "error": "invalid_state"
}
```

### 3. Revert Payment

Reverts a payment or issues a refund to the customer when an order is canceled.

**Endpoint:** `POST /api/payment/{order_id}/revert`

**Request Body (optional):**
```json
{
  "reason": "order_canceled"
}
```

**Sample Request (cURL):**
```bash
curl -X POST http://localhost:3003/api/payment/order_123abc/revert \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "order_canceled"
  }'
```

**Successful Response (200 OK):**
```json
{
  "success": true,
  "description": "Payment reverted successfully",
  "status": "FAILED"
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "description": "Payment not found"
}
```

### 4. Stripe Webhook

Handles events from Stripe, such as successful payments, cancellations, or failures.

**Endpoint:** `POST /api/stripe-webhook`

This endpoint expects a raw request body from Stripe with a signature in the headers. It can't be easily tested with regular API tools without proper Stripe webhook signatures.

**Response:** 200 OK with empty body for successful processing.

## Testing Guide

### Prerequisites

Before testing the payment service, ensure:

1. The service is running (via Docker Compose or locally)
2. You have Stripe API keys in test mode
3. You've configured the webhook endpoint in Stripe (for webhook tests)

### Testing with Sample Data

#### 1. Setting Up a User with Payment Method

A user with payment information should be available in the User Service database. The user information used in our examples:

```json
{
  "success": true,
  "user": {
    "clerkUserId": "user_2uFnauOsxFRGIoy3O5CJA6v5sM6",
    "createdAt": "2025-03-29T11:07:22.908198",
    "customerRating": 5.0,
    "email": "shariffar.2023@smu.edu.sg",
    "firstName": "Shariff",
    "lastName": "Rashid",
    "phoneNumber": "+6591800745",
    "runnerRating": 5.0,
    "updatedAt": "2025-03-29T11:08:03.326261",
    "userStripeCard": {
      "brand": "visa",
      "exp_month": 4,
      "exp_year": 2025,
      "last4": "4242",
      "payment_method_id": "pm_1R7xF8QR8BO665MwbdEmL3Pz",
      "updated_at": "2025-03-29T11:08:03.326151+00:00"
    },
    "username": "binkers2134"
  }
}
```

#### 2. Creating an Order

For testing, we need an order in the system. A sample order:

```json
{
  "order_id": "order_abc123",
  "cust_id": "user_2uFnauOsxFRGIoy3O5CJA6v5sM6",
  "order_description": "[{\"name\":\"Burger\",\"price\":12.99,\"quantity\":1},{\"name\":\"Fries\",\"price\":3.99,\"quantity\":1}]",
  "food_fee": 16.98,
  "delivery_fee": 3.99,
  "delivery_location": "123 Campus Street",
  "order_status": "PENDING"
}
```

#### 3. Complete Payment Flow Testing

**Step 1: Authorize Payment**

```bash
curl -X POST http://localhost:3003/api/payment/order_abc123/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {
      "clerkUserId": "user_2uFnauOsxFRGIoy3O5CJA6v5sM6",
      "userStripeCard": {
        "payment_method_id": "pm_1R7xF8QR8BO665MwbdEmL3Pz"
      }
    }
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "description": "Payment authorized successfully and held in escrow",
  "paymentId": "payment_abc123",
  "paymentIntentId": "pi_abc123",
  "status": "AUTHORIZED"
}
```

**Step 2: Release Payment to Runner**

```bash
curl -X POST http://localhost:3003/api/payment/order_abc123/release \
  -H "Content-Type: application/json" \
  -d '{
    "runnerId": "user_456"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "description": "Funds released to runner successfully",
  "status": "RELEASED",
  "runnerId": "user_456"
}
```

**Alternative Step 2: Revert Payment (Cancellation)**

```bash
curl -X POST http://localhost:3003/api/payment/order_abc123/revert \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "order_canceled"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "description": "Payment reverted successfully",
  "status": "FAILED"
}
```

### Testing with Stripe Test Cards

For testing payments, use Stripe's test cards:

| Card Number | Description |
|-------------|-------------|
| 4242 4242 4242 4242 | Successful payment |
| 4000 0000 0000 9995 | Payment requires authentication |
| 4000 0000 0000 0002 | Payment declined |

For any test card, use:
- Any future expiration date (e.g., 12/25)
- Any 3-digit CVC code
- Any ZIP code

## Integration with Other Services

The Payment Service integrates with several other services in the CampusG platform:

### User Service Integration

- **Purpose**: Retrieves payment methods stored for users
- **Endpoint Used**: `GET /api/user/{clerk_user_id}/payment`
- **Data Exchanged**: Payment method IDs and card details

### Order Service Integration

- **Purpose**: Gets order details including amount to be charged
- **Implementation**: The payment service will fetch order details to determine payment amount
- **Note**: In the current implementation, this is mocked for testing purposes

### Kafka Event Integration

The payment service publishes events to Kafka for other services to consume:

| Event | Topic | Description |
|-------|-------|-------------|
| `payment.authorized` | payment-events | When a payment is authorized and held in escrow |
| `payment.released` | payment-events | When funds are released to a runner |
| `payment.reverted` | payment-events | When a payment is canceled or refunded |

## Stripe Integration

### Overview

The Payment Service uses Stripe as the payment processor, specifically using:

1. **Payment Intents API**: For securely processing payments
2. **Manual Capture Feature**: To implement escrow functionality
3. **Webhooks**: To receive asynchronous events from Stripe

### Key Integration Points

1. **Payment Authorization**:
   - Creates a Payment Intent with `capture_method="manual"` to hold funds without charging
   - Attaches metadata for order ID and customer ID

2. **Fund Release**:
   - Uses the Stripe Payment Intent Capture API to move funds from authorization to charge
   - Updates metadata with runner ID and completion timestamp

3. **Payment Reversal**:
   - For uncaptured payments: Cancels the Payment Intent
   - For captured payments: Creates a Refund

### Webhook Handling

The service processes the following Stripe webhook events:

1. `payment_intent.succeeded`: Payment was successfully processed
2. `payment_intent.canceled`: Payment was canceled
3. `payment_intent.payment_failed`: Payment processing failed

## Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Issues

**Symptoms**: Service fails to start with database connection errors

**Solutions**:
- Check if the payment-db container is running: `docker-compose ps payment-db`
- Verify the database connection string: `docker-compose logs payment-service`
- Try manually connecting to the database: `docker-compose exec payment-db psql -U postgres -d payment_db`

#### 2. Stripe API Key Issues

**Symptoms**: Payment authorization fails with authentication errors

**Solutions**:
- Verify your Stripe API key in the `.env` file
- Ensure you're using the correct key type (test vs. production)
- Check Stripe dashboard for key restrictions

#### 3. Payment Authorization Failures

**Symptoms**: Payments fail during authorization

**Solutions**:
- Check Stripe dashboard for detailed error messages
- Verify the payment method exists and is valid
- For test mode, ensure you're using valid test card numbers

#### 4. Webhook Integration Issues

**Symptoms**: Webhooks aren't being processed

**Solutions**:
- Verify webhook URL is accessible from Stripe
- Check webhook secret matches in Stripe dashboard and `.env` file
- Use Stripe CLI to test webhook delivery: `stripe listen --forward-to localhost:3003/api/stripe-webhook`

### Logs and Debugging

To view service logs:

```bash
# View logs for the payment service
docker-compose logs payment-service

# Follow logs in real-time
docker-compose logs -f payment-service

# View the last 100 lines
docker-compose logs --tail=100 payment-service
```

To enable debug logging, set the `FLASK_ENV` environment variable to `development`:

```
FLASK_ENV=development
```

### Health Check

To verify if the service is running correctly:

```bash
curl http://localhost:3003/health
```

Expected response:
```json
{"status": "healthy"}
```
