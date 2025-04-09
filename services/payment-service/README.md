# Payment Service

## Overview

This service handles payment processing for the CampusG application, integrating primarily with Stripe. It manages payment records, processes payment commands via Kafka (originating from saga orchestrators), and listens to Stripe webhooks for asynchronous updates.

## Technology Stack

- **Framework**: Flask
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Payment Gateway**: Stripe
- **Messaging**: Kafka
- **Container**: Docker
- **Language**: Python

## HTTP API Endpoints

The service exposes a limited set of HTTP endpoints, as core payment actions are handled asynchronously via Kafka and Stripe webhooks.

*   **`GET /health`**:
    *   **Purpose:** Basic health check.
    *   **Response:** `{'status': 'healthy'}`

*   **`GET /payment/<order_id>/status`**:
    *   **Purpose:** Retrieves the current status and details of the payment associated with a specific `order_id`.
    *   **Path Parameter:** `order_id` (string)
    *   **Response:** Payment object or 404.

*   **`GET /payment/<payment_id>/details`**:
    *   **Purpose:** Retrieves detailed information about a specific payment using its internal `payment_id` (UUID).
    *   **Path Parameter:** `payment_id` (string, UUID)
    *   **Response:** Payment object or 404.

*   **`GET /history/<user_id>`**:
    *   **Purpose:** Retrieves a summary of a user's payment history, including total amounts and counts for money spent (as customer) and earned (as runner).
    *   **Path Parameter:** `user_id` (string, Clerk User ID)
    *   **Response:** `{ "userId": ..., "totalSpent": ..., "totalEarned": ..., "spentCount": ..., "earnedCount": ... }`

*   **`POST /payment/<payment_id>/release`**:
    *   **Purpose:** API trigger to publish a `release_payment` command to Kafka. This initiates payment capture and transfer to the runner.
    *   **Path Parameter:** `payment_id` (string, UUID)
    *   **Request Body:** `{ "runner_id": "...", "runner_connect_account_id": "acct_..." }` (Required)
    *   **Response:** 202 Accepted with `correlation_id`.

*   **`POST /payment/<payment_id>/revert`**:
    *   **Purpose:** API trigger to publish a `revert_payment` command to Kafka. This initiates payment cancellation or refund.
    *   **Path Parameter:** `payment_id` (string, UUID)
    *   **Request Body:** `{ "reason": "..." }` (Optional)
    *   **Response:** 202 Accepted with `correlation_id`.

*   **`POST /stripe-webhook`**:
    *   **Purpose:** Handles incoming webhook events from Stripe. Verifies signature and processes relevant events (`payment_intent.succeeded`, `payment_intent.canceled`, `payment_intent.payment_failed`). Updates local payment status and publishes Kafka events (`payment.authorized`, `payment.failed`).
    *   **Security:** Requires `STRIPE_WEBHOOK_SECRET` environment variable to be set for signature verification.
    *   **Response:** 200 OK to acknowledge receipt to Stripe.

## Kafka Interactions

The service relies on Kafka for orchestrating payment workflows.

*   **Consumer:**
    *   **Topic:** `payment_commands` (Default name)
    *   **Group ID:** `payment-service-group` (Default name)
    *   **Consumed Command Types:**
        *   `type: 'authorize_payment'`
            *   **Expected Payload:** `{ "customer_id": "...", "payment_method_id": "pm_...", "amount": ..., "currency": "...", "order_id": "...", "correlation_id": "..." }`
            *   **Action:** Creates a `Payment` record, initiates a Stripe PaymentIntent (authorize only), updates status to `INITIATING` or `REQUIRES_ACTION`. Publishes `payment.authorized` or `payment.failed` event based on Stripe's immediate response.
        *   `type: 'release_payment'`
            *   **Expected Payload:** `{ "payment_id": "...", "runner_id": "...", "runner_connect_account_id": "acct_...", "correlation_id": "..." }`
            *   **Action:** Captures the authorized Stripe PaymentIntent, initiates a Stripe Transfer to the runner's Connect account. Updates status to `SUCCEEDED`. Publishes `payment.released` or `payment.failed` event.
        *   `type: 'revert_payment'`
            *   **Expected Payload:** `{ "payment_id": "...", "reason": "..." (optional), "correlation_id": "..." }`
            *   **Action:** Cancels the Stripe PaymentIntent (if not captured) or creates a Stripe Refund (if captured). Updates status to `REVERTED`. Publishes `payment.failed` event (or a specific `payment.reverted` event if needed).

*   **Producer:**
    *   **Topic:** `payment_events` (Default name)
    *   **Produced Event Types:**
        *   `type: 'payment.authorized'`
            *   **Trigger:** Successful Stripe PaymentIntent authorization (either immediate or via webhook after user action).
            *   **Payload:** `{ "payment_id": "...", "order_id": "...", "payment_intent_id": "pi_...", "status": "AUTHORIZED" or "SUCCEEDED", "correlation_id": "..." }`
        *   `type: 'payment.failed'`
            *   **Trigger:** Failure during authorization, capture, revert, or via Stripe webhook (`payment_intent.canceled`, `payment_intent.payment_failed`).
            *   **Payload:** `{ "error": "...", "message": "...", "stripe_code": "..." (optional), "payment_id": "...", "order_id": "...", "correlation_id": "..." }`
        *   `type: 'payment.released'`
            *   **Trigger:** Successful Stripe PaymentIntent capture and successful transfer initiation.
            *   **Payload:** `{ "payment_id": "...", "order_id": "...", "transfer_id": "tr_...", "correlation_id": "..." }`

## Database Models

- `Payment`: Stores details about each payment attempt, including `order_id`, `customer_id`, `runner_id`, `amount`, `status`, `stripe_payment_intent_id`, `stripe_transfer_id`, etc.
- `PaymentStatus`: Enum defining possible payment statuses (`INITIATING`, `REQUIRES_ACTION`, `AUTHORIZED`, `SUCCEEDED`, `FAILED`, `REVERTED`).

## Setup & Running

(Refer to standard Flask app setup using `requirements.txt`, `run.py`, and Docker configuration.)

**Environment Variables:**
*   `STRIPE_SECRET_KEY`: Your Stripe secret API key.
*   `STRIPE_WEBHOOK_SECRET`: Secret for verifying incoming Stripe webhooks.
*   `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker addresses.
*   Database connection variables (e.g., `DATABASE_URL`).
