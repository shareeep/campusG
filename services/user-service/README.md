# User Service

## Overview

This service manages user data, including profile information, ratings, and payment details (integrated with Stripe and Clerk). It provides HTTP endpoints for CRUD operations and interacts with Kafka for asynchronous tasks related to payment information retrieval.

## HTTP API Endpoints

The service exposes the following Flask-based HTTP endpoints:

*   **`GET /health`**:
    *   **Purpose:** Basic health check.
    *   **Response:** `{'status': 'healthy'}`

*   **`POST /user/temp`**:
    *   **Purpose:** Creates a temporary user record. Primarily for testing or specific initial setup scenarios.
    *   **Request Body:** `{ "email": "...", "first_name": "...", "last_name": "..." }` (email required)
    *   **Response:** Success/failure message, created user details.

*   **`GET /user/<clerk_user_id>`**:
    *   **Purpose:** Retrieves full user details by Clerk User ID.
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Query Parameter:** `includePaymentDetails` (boolean, default: true) - Whether to include payment details in the response.
    *   **Response:** User object (including payment details if requested) or 404 if not found.

*   **`GET /user/<clerk_user_id>/payment`**:
    *   **Purpose:** Retrieves only the user's primary payment information (formatted for frontend).
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Response:** Payment details (`payment_method_id`, `last_four`, `card_type`, `expiry_month`, `expiry_year`) or 404/400.

*   **`GET /user/<clerk_user_id>/connect-account`**:
    *   **Purpose:** Retrieves the user's Stripe Connect account ID.
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Response:** `{ "success": true, "stripe_connect_account_id": "acct_..." }` or 404.

*   **`PUT /user/<clerk_user_id>/payment`**:
    *   **Purpose:** Updates the user's primary payment method using a Stripe PaymentMethod ID.
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Request Body:** `{ "paymentMethodId": "pm_..." }`
    *   **Response:** Success/failure message.

*   **`DELETE /user/<clerk_user_id>/payment`**:
    *   **Purpose:** Deletes the user's primary payment method information from the service's database.
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Response:** Success/failure message.
    *   *Note: Functionally similar to `DELETE /user/<clerk_user_id>/payment-methods`.*

*   **`POST /user/<clerk_user_id>/update-customer-rating`**:
    *   **Purpose:** Updates the user's customer rating.
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Request Body:** `{ "rating": 4.5 }`
    *   **Response:** Success/failure message.

*   **`POST /user/<clerk_user_id>/update-runner-rating`**:
    *   **Purpose:** Updates the user's runner rating.
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Request Body:** `{ "rating": 4.8 }`
    *   **Response:** Success/failure message.

*   **`GET /user/list-users`**:
    *   **Purpose:** Retrieves a list of all Clerk user IDs stored in the system. Useful for debugging/testing.
    *   **Response:** `{ "success": true, "userIds": ["user_...", "user_..."] }`

*   **`PUT /user/<clerk_user_id>/connect-account`**:
    *   **Purpose:** Updates the user's Stripe Connect account ID.
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Request Body:** `{ "stripe_connect_account_id": "acct_..." }`
    *   **Response:** Success/failure message and updated user details.

*   **`POST /user/<clerk_user_id>/payment-methods`**:
    *   **Purpose:** Adds a new Stripe PaymentMethod to the user, attaches it to their Stripe Customer, and sets it as the default payment method. Stores card details in the service DB.
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Request Body:** `{ "payment_method_id": "pm_..." }`
    *   **Response:** Success/failure message and payment info.

*   **`DELETE /user/<clerk_user_id>/payment-methods`**:
    *   **Purpose:** Deletes the user's primary payment method information from the service's database.
    *   **Path Parameter:** `clerk_user_id` (string)
    *   **Response:** Success/failure message.
    *   *Note: Functionally similar to `DELETE /user/<clerk_user_id>/payment`.*

*   **`POST /user/sync-from-frontend`**:
    *   **Purpose:** Creates a new user or updates an existing user based on data provided (typically synced from Clerk via the frontend). Handles creation of associated Stripe Customer and Connect accounts for new users.
    *   **Request Body:** `{ "clerk_user_id": "...", "email": "...", "first_name": "...", ... }`
    *   **Response:** Success/failure message and the full synced user object.

## Kafka Interactions

The service uses Kafka for asynchronous communication, primarily related to payment information requests initiated by saga orchestrators.

*   **Consumer:**
    *   **Topic:** `user_commands` (Configurable via `KAFKA_USER_COMMANDS_TOPIC`)
    *   **Group ID:** `user-service-group` (Configurable via `KAFKA_USER_SERVICE_GROUP_ID`)
    *   **Consumed Message Types:**
        *   `type: 'get_payment_info'`
            *   **Expected Payload:** `{ "user_id": "clerk_user_id_...", "correlation_id": "..." }`
            *   **Action:** Retrieves the user's Stripe Customer ID and default PaymentMethod ID.

*   **Producer:**
    *   **Topic:** `user_events` (Configurable via `KAFKA_USER_EVENTS_TOPIC`)
    *   **Produced Message Types:**
        *   `type: 'user.payment_info_retrieved'`
            *   **Trigger:** Successful retrieval of payment info requested via `get_payment_info` command.
            *   **Payload:** `{ "payment_info": { "stripeCustomerId": "cus_...", "paymentMethodId": "pm_..." }, "correlation_id": "...", "timestamp": "...", "source": "user-service" }`
        *   `type: 'user.payment_info_failed'`
            *   **Trigger:** Failure to retrieve payment info (e.g., user not found, payment method missing).
            *   **Payload:** `{ "error": "Reason for failure", "correlation_id": "...", "timestamp": "...", "source": "user-service" }`
