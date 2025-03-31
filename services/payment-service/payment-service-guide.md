# CampusG Payment Service Guide

> **WORK IN PROGRESS**: We are currently implementing Stripe customer ID integration. The API endpoints documented below don't yet reflect these upcoming changes.

## Upcoming: Stripe Customer ID Integration

We are enhancing the Payment Service to use Stripe customer IDs from the User Service. This will improve payment processing by:

1. Eliminating duplicate customer creation in Stripe
2. Enabling saved payment methods across transactions
3. Reducing API calls to Stripe during payment processing

### User Service Integration

The User Service already stores Stripe customer IDs as shown in the `User` model:

```python
class User(db.Model):
    # ...existing code...
    user_stripe_card = db.Column(JSONB, nullable=True)
    # ...existing code...
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    # ...existing code...
```

The User Service handles customer creation in Stripe via the endpoint:

```python
@api.route('/user/<clerk_user_id>/payment-methods', methods=['POST'])
def add_payment_method(clerk_user_id):
    # ...existing code...
    # Create or retrieve Stripe customer
    if not user.stripe_customer_id:
        # Create a new Stripe customer
        customer = stripe.Customer.create(
            metadata={'clerk_user_id': clerk_user_id},
            email=user.email,
            name=f"{user.first_name} {user.last_name}"
        )
        user.stripe_customer_id = customer.id
        db.session.commit()
    # ...existing code...
```

### Payment Service Updates (Coming Soon)

The Payment Service will soon be updated to:

1. Accept `stripeCustomerId` in payment requests
2. Use existing Stripe customers rather than creating temporary ones
3. Support saved payment methods

Example of future request format:
```json
{
  "customer": {
    "clerkUserId": "user_2uFnauOsxFRGIoy3O5CJA6v5sM6",
    "stripeCustomerId": "cus_1234567890",
    "userStripeCard": {
      "payment_method_id": "pm_1R7xF8QR8BO665MwbdEmL3Pz"
    }
  },
  "order": {
    "amount": 2098,
    "description": "Order with ID order_123abc - CampusG Escrow"
  }
}
```

> Note: The API documentation below shows the current implementation and will be updated when the Stripe customer ID integration is complete.

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
10. [Monitoring Payments](#monitoring-payments)

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

Create a `.env` file in the project root with:

```
# Stripe configuration
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Service URLs (when running locally outside Docker)
USER_SERVICE_URL=http://localhost:3001
ORDER_SERVICE_URL=http://localhost:3002
```

### Starting the Service

```bash
# From the project root directory
cd c:\whereYouStoreProject\campusG

# Start the payment service and its database
docker-compose build payment-service
docker-compose up payment-db payment-service 
```

The payment service runs on port 3003.

### Configuring Stripe Webhooks

1. Sign in to Stripe Dashboard > Developers > Webhooks
2. Expose with `ngrok http 3003`
3. Add endpoint: `http://your-ngrok-link/api/stripe-webhook`
4. Subscribe to: `payment_intent.succeeded`, `payment_intent.canceled`, `payment_intent.payment_failed`
5. Copy the signing secret to your `.env` file

## Database Integration

The payment service uses PostgreSQL to store payment records.

### Database Schema

| Field | Type | Description |
|-------|------|-------------|
| id | String | Primary key, UUID format |
| payment_intent_id | String | Stripe payment intent ID |
| order_id | String | Associated order ID |
| customer_id | String | Customer who made the payment |
| runner_id | String | Runner to receive the payment |
| amount | Decimal | Payment amount in USD |
| status | String | Payment status (INITIATING, AUTHORIZED, RELEASED, REVERTED, FAILED) |
| description | String | Payment description |
| created_at | DateTime | Timestamp when record was created |
| updated_at | DateTime | Timestamp when record was last updated |

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
  "order": {
    "amount": 2098,
    "description": "Order with ID order_123abc - CampusG Escrow"
  },
  "custpaymentId": "optional_custom_payment_id",
  "return_url": "https://campusg.com/order-confirmation"
}
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

### 2. Release Payment

Releases the payment from escrow to the runner when an order is successfully completed.

**Endpoint:** `POST /api/payment/{order_id}/release`

**Request Body:**
```json
{
  "runnerId": "user_abc123"
}
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

### 3. Revert Payment

Reverts a payment or issues a refund to the customer when an order is canceled.

**Endpoint:** `POST /api/payment/{order_id}/revert`

**Request Body (optional):**
```json
{
  "reason": "order_canceled"
}
```

**Successful Response (200 OK):**
```json
{
  "success": true,
  "description": "Payment reverted successfully",
  "status": "FAILED"
}
```

### 4. Stripe Webhook

Handles events from Stripe, such as successful payments, cancellations, or failures.

**Endpoint:** `POST /api/stripe-webhook`

This endpoint expects a raw request body from Stripe with a signature in the headers.

**Response:** 200 OK with empty body for successful processing.

### 5. Check Payment Status

Retrieves the status and details of a payment for a specific order.

**Endpoint:** `GET /api/payment/{order_id}/status`

**Successful Response (200 OK):**
```json
{
  "success": true,
  "payment": {
    "paymentId": "payment_abc123",
    "orderId": "order_123abc",
    "customerId": "user_2uFnauOsxFRGIoy3O5CJA6v5sM6",
    "runnerId": "user_456",
    "amount": 20.98,
    "status": "AUTHORIZED",
    "description": "Order order_123abc - CampusG Escrow",
    "paymentIntentId": "pi_abc123",
    "createdAt": "2025-03-29T11:08:03.326151+00:00",
    "updatedAt": "2025-03-29T11:08:03.326151+00:00"
  }
}
```

### 6. Get Payment Details

Retrieves detailed information about a specific payment using the payment ID.

**Endpoint:** `GET /api/payment/{payment_id}/details`

**Successful Response (200 OK):**
```json
{
  "success": true,
  "payment": {
    "paymentId": "payment_abc123",
    "orderId": "order_123abc",
    "customerId": "user_2uFnauOsxFRGIoy3O5CJA6v5sM6",
    "runnerId": "user_456",
    "amount": 20.98,
    "status": "AUTHORIZED",
    "description": "Order order_123abc - CampusG Escrow",
    "paymentIntentId": "pi_abc123",
    "createdAt": "2025-03-29T11:08:03.326151+00:00",
    "updatedAt": "2025-03-29T11:08:03.326151+00:00"
  }
}
```

### Return URL Configuration

When authorizing payments, include a `return_url` parameter:
```json
{
  "return_url": "http://localhost:5173/customer/order-form"
}
```

Stripe will redirect users to this URL after they complete authentication or payment.

## Testing Guide

### Prerequisites

1. Running service (via Docker Compose)
2. Stripe API keys in test mode
3. Configured webhook endpoint

### Test Flow

1. **Authorize Payment**: Create a payment using test card
2. **Release or Revert**: Test both payment completion and cancellation flows
3. **Check Status**: Verify payment status via API endpoints

### Stripe Test Cards

| Card Number | Description |
|-------------|-------------|
| 4242 4242 4242 4242 | Successful payment |
| 4000 0000 0000 3220 | Requires authentication |
| 4000 0000 0000 0002 | Payment declined |

For all test cards, use any future expiration date, any CVC, and any ZIP code.

### Monitoring Test Payments

1. **API Endpoints**: Check status via the service API
2. **Stripe Dashboard**: View payments at dashboard.stripe.com/test/payments
3. **Stripe CLI**: Use `stripe listen --forward-to localhost:3003/api/stripe-webhook`

## Integration with Other Services

The Payment Service follows a request-based integration model where:

1. **Client Applications**:
   - Collect necessary data from User and Order Services
   - Pass all required data in payment API requests

2. **Payment Service**:
   - Processes payment operations based on provided data
   - Publishes payment events to Kafka for asynchronous communication

This approach reduces inter-service dependencies and improves system resilience.

## Stripe Integration

### Escrow Implementation

The service implements escrow using Stripe features:

1. **Authorization**: Funds reserved using `capture_method="manual"`
2. **Release**: Capture previously authorized payment when order completes
3. **Revert**: Cancel payment intent when order is canceled

### Webhook Handling

The service processes these Stripe webhook events:
- `payment_intent.succeeded`: Payment processed successfully
- `payment_intent.canceled`: Payment canceled
- `payment_intent.payment_failed`: Payment failed

## Troubleshooting

### Common Issues

1. **Database Connection Issues**: Check container status and connection string
2. **Stripe API Key Issues**: Verify API keys in `.env` file
3. **Payment Failures**: Check Stripe dashboard for detailed error messages
4. **Webhook Issues**: Verify URL accessibility and webhook secret

### Health Check

```bash
curl http://localhost:3003/health
```

Expected response: `{"status": "healthy"}`

## Monitoring Payments

1. **Service API**: Use status endpoints to track payments
2. **Stripe Dashboard**: Access comprehensive payment monitoring
3. **Application Logs**: Check Docker logs for detailed information
   ```bash
   docker-compose logs -f payment-service
   ```
