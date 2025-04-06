# User Service: Payment Data Flow Guide

This document outlines the data required from User Service for payment processing via Kafka, the Create Order Saga, and eventual submission to Stripe.

## Data Flow Overview

```
User Service → Kafka (user_events) → Create Order Saga → Kafka (payment_commands) → Payment Service → Stripe
```

## Required User Data for Payment Processing

When the User Service responds to a payment information request, it must provide the following data to the Kafka topic `user_events`:

### Message Structure

```json
{
  "type": "user.payment_info_retrieved",
  "correlation_id": "<saga_id>",
  "timestamp": "2025-03-31T10:30:00Z",
  "payload": {
    "customer": {
      "clerkUserId": "<clerk_user_id>",
      "stripeCustomerId": "<stripe_customer_id>",
      "userStripeCard": {
        "payment_method_id": "<payment_method_id>",
        "card_type": "visa",
        "last_four": "4242"
      }
    },
    "order": {
      "amount": 1299,
      "description": "Food delivery order"
    }
  },
  "source": "user-service"
}
```

### Critical Data Elements

1. **Stripe Customer ID (`stripeCustomerId`)**
   - This is the unique identifier for the customer in Stripe
   - Stored in the User model's `stripe_customer_id` field
   - **MUST** be valid and previously created in Stripe

2. **Payment Method ID (`payment_method_id`)**
   - Identifies the specific payment method (card, bank account, etc.)
   - Stored in the User model's `user_stripe_card` JSONB field
   - Example: `pm_card_visa` for test Visa card

3. **Amount**
   - Payment amount in cents (e.g., 1299 for $12.99)
   - Should be calculated based on the order total
   - Must be a positive integer

## Implementation Notes

### 1. Retrieving User Payment Data

When responding to payment info requests, you must:

```python
def get_user_payment_info(clerk_user_id):
    """
    Retrieves payment information for a user to be passed to payment service
    """
    # Fetch user from database
    user = User.query.filter_by(clerk_user_id=clerk_user_id).first()
    
    if not user or not user.stripe_customer_id:
        # Handle error - user not found or missing stripe customer ID
        return None
    
    # Format payment data as needed by the saga
    payment_info = {
        "customer": {
            "clerkUserId": user.clerk_user_id,
            "stripeCustomerId": user.stripe_customer_id,
            "userStripeCard": user.user_stripe_card or {}
        }
    }
    
    return payment_info
```

### 2. Publishing to Kafka

When publishing user payment info to Kafka:

```python
def publish_payment_info(correlation_id, user_id, order_data):
    """
    Publishes payment information to Kafka for create-order-saga
    """
    # Get user payment info
    payment_info = get_user_payment_info(user_id)
    
    if not payment_info:
        # Handle error case
        publish_error_event(correlation_id)
        return False
    
    # Construct complete message
    message = {
        "type": "user.payment_info_retrieved",
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "customer": payment_info["customer"],
            "order": {
                "amount": order_data["amount"],
                "description": order_data["description"]
            }
        },
        "source": "user-service"
    }
    
    # Publish to Kafka
    kafka_service.producer.produce("user_events", json.dumps(message))
    kafka_service.producer.flush()
    
    return True
```

## What Happens Next?

1. The Create Order Saga orchestrator receives the `user.payment_info_retrieved` event
2. It combines this information with the order details
3. It sends an `authorize_payment` command to the `payment_commands` topic
4. The Payment Service receives this command and:
   - Creates a record in its database
   - Calls Stripe API to create a PaymentIntent
   - Sets `capture_method: 'manual'` for escrow functionality
   - Responds with `payment.authorized` or `payment.failed` event

## Required Stripe Configuration

To ensure proper functioning:

1. Ensure User Service correctly stores Stripe Customer IDs when users are created
2. Verify that payment methods are properly saved to user accounts
3. For testing, use Stripe test mode with test cards:
   - `pm_card_visa` - Successful payment
   - `pm_card_visa_chargeDeclined` - Declined payment
   - See [Stripe testing documentation](https://stripe.com/docs/testing) for more test cards

## Troubleshooting

**Common Issues:**

1. **"Invalid Stripe Customer ID"** - Ensure the user has a valid `stripe_customer_id` in their record
2. **"Payment method not found"** - Verify the user has saved payment methods in Stripe
3. **"Missing return_url"** - If Stripe dashboard has redirect-based methods enabled, the return_url is required

If payments are failing, check the Stripe Dashboard logs for detailed error information.
