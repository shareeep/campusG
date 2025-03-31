# Payment Service - Setup, Changelog, and Testing Guide (March 31, 2025)

This document outlines the recent changes made to the Payment Service and provides steps for testing its integration with Stripe and Kafka.

## Changelog

The Payment Service has been refactored to operate in an event-driven manner, integrating with the Create Order Saga via Kafka and handling Stripe interactions internally.

Key changes include:

1.  **Kafka Integration:**
    *   Implemented a functional Kafka client (`kafka-python`) in `app/services/kafka_service.py`.
    *   The service now consumes `authorize_payment` commands from the `payment_commands` topic.
    *   It publishes `payment.authorized` and `payment.failed` events to the `payment_events` topic, including the necessary `correlation_id`.
2.  **Stripe Integration:**
    *   Updated `app/services/stripe_service.py` to handle the `authorize_payment` Kafka command.
    *   Payment Intent creation now uses the `stripeCustomerId` provided in the command payload.
    *   Utilizes Stripe's `capture_method: 'manual'` for escrow functionality.
3.  **Event-Driven Flow:**
    *   Removed direct API endpoints for `/authorize`, `/release`, and `/revert` in `app/api/payment_routes.py`. Payment authorization is now solely triggered by the Kafka command. Release/revert actions will be handled by other sagas or future webhook logic.
    *   Status/details endpoints (`/payment/<order_id>/status`, `/payment/<payment_id>/details`) remain for querying.
4.  **Stripe Webhook Handling:**
    *   Implemented `/api/stripe-webhook` in `app/api/webhook_routes.py`.
    *   Verifies webhook signatures using the `STRIPE_WEBHOOK_SECRET`.
    *   Handles `payment_intent.succeeded`, `payment_intent.canceled`, and `payment_intent.payment_failed` events.
    *   Updates the local database status accordingly.
    *   Publishes `payment.authorized` or `payment.failed` Kafka events based on webhook outcomes (especially important after a `requires_action` state during initial authorization).
5.  **Database Model:**
    *   Updated `app/models/models.py` to use SQLAlchemy's `Enum` type for the `status` field for better type safety.
6.  **Configuration:**
    *   Updated `docker-compose.yml` to include necessary environment variables (`KAFKA_BOOTSTRAP_SERVERS`, `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`) for the `payment-service`, referencing the root `.env` file.
    *   Corrected variable names in the root `.env` file (`STRIPE_PUBLISHABLE_KEY`).
7.  **Application Initialization:**
    *   Updated `app/__init__.py` to initialize the Kafka service, register the `handle_authorize_payment_command` handler, and set up Kafka consumer/producer lifecycle management.

### Recent Fixes (March 31, 2025)

1. **Flask Application Context Fix:**
   * Fixed issue where database operations were failing in background threads without a Flask application context
   * Modified `app/services/kafka_service.py` to store the Flask app instance and run handlers within an app context
   * Updated `app/__init__.py` to pass the Flask app to the Kafka service

2. **Database Schema Fix:**
   * Fixed database schema mismatch between SQLAlchemy model and database table
   * Ensured proper creation of the 'id' column in the 'payments' table
   * Verified proper database operations in Kafka message handlers

3. **Kafka Integration Testing:**
   * Added testing tools and scripts to verify Kafka connectivity:
     * `services/create-order-saga-orchestrator/fixed_kafka_test_producer.py` - For reliable message sending to Kafka
     * `services/create-order-saga-orchestrator/test_payment_integration.py` - For end-to-end Kafka integration testing
     * `services/create-order-saga-orchestrator/docker_test_payment_service.sh` - For Docker container testing

## Testing Guide

Follow these steps to test the Payment Service integration:

### Prerequisites

1.  **Docker & Docker Compose:** Ensure they are installed and running.
2.  **`.env` File:** Verify the root `.env` file contains the correct **Test** keys:
    *   `STRIPE_SECRET_KEY` (sk_test_...)
    *   `STRIPE_PUBLISHABLE_KEY` (pk_test_...)
    *   `STRIPE_WEBHOOK_SECRET` (whsec_test_...)
3.  **`ngrok`:** Install `ngrok` if you haven't already. ([Download](https://ngrok.com/download))

### Steps

1.  **Start `ngrok`:**
    *   Open a terminal and run:
        ```bash
        ngrok http 3003
        ```
    *   Copy the `https://<random-string>.ngrok-free.app` URL provided by `ngrok`.
    *   **Keep this terminal open.**

2.  **Configure Stripe Webhook Endpoint (if not already done):**
    *   Go to your [Stripe Test Dashboard](https://dashboard.stripe.com/test/webhooks).
    *   Click "Add endpoint".
    *   Paste the `ngrok` URL and append `/api/stripe-webhook` (e.g., `https://<random-string>.ngrok-free.app/api/stripe-webhook`).
    *   Select the events to listen to:
        *   `payment_intent.succeeded`
        *   `payment_intent.canceled`
        *   `payment_intent.payment_failed`
    *   Click "Add endpoint". Ensure the Signing Secret matches the `STRIPE_WEBHOOK_SECRET` in your `.env` file.

3.  **Start Services:**
    *   Open another terminal in the project root (`c:/Users/Bjorn/Documents/GitHub/campusG`).
    *   Run the following command to build (if necessary) and start the required services:
        ```bash
        docker-compose up --build payment-db payment-service create-order-saga-db create-order-saga-orchestrator kafka zookeeper user-db user-service order-db order-service
        ```
    *   Wait for the services to initialize. Check the logs for any errors, especially related to Kafka connections or Stripe key configuration in the `payment-service`.

4.  **Testing with the Integration Script:**
    * Copy the test script and producer to the create-order-saga-orchestrator container:
      ```bash
      docker cp services/create-order-saga-orchestrator/fixed_kafka_test_producer.py campusg-create-order-saga-orchestrator-1:/app/
      docker cp services/create-order-saga-orchestrator/test_payment_integration.py campusg-create-order-saga-orchestrator-1:/app/
      ```
    * Run the integration test inside the container:
      ```bash
      docker exec -it campusg-create-order-saga-orchestrator-1 bash -c "cd /app && python3 test_payment_integration.py"
      ```
    * In a separate terminal, monitor the Kafka messages:
      ```bash
      docker exec -it campusg-kafka-1 kafka-console-consumer --bootstrap-server kafka:9092 --topic payment_commands --from-beginning
      ```

5.  **Trigger the Create Order Saga (Alternative Method):**
    *   You need to initiate the Create Order Saga. This typically involves making an API call to the `create-order-saga-orchestrator` service (running on port 3101 locally). The exact API endpoint and payload depend on how that service is designed.
    *   The request should include customer details, order details, and payment amount.
    *   *Alternatively*, if a test script exists (like `test_create_order_saga.sh` or `test_saga.py` in the orchestrator's directory), you might be able to use that. You may need to adapt it to run within the Docker environment or against the exposed port.

6.  **Observe Logs:**
    *   Monitor the logs from `docker-compose up`. Pay close attention to:
        *   **`create-order-saga-orchestrator`:** Look for logs indicating it's publishing the `authorize_payment` command to Kafka.
        *   **`payment-service`:** Look for logs indicating:
            *   It received the `authorize_payment` command.
            *   It's attempting to create a Stripe Payment Intent.
            *   It published `payment.authorized` or `payment.failed` back to Kafka.
            *   It received webhook events from Stripe (via `ngrok`).
        *   **`create-order-saga-orchestrator`:** Look for logs indicating it received the `payment.authorized` or `payment.failed` event from Kafka and proceeded with the saga or handled the failure.

7.  **Check Stripe Dashboard:**
    *   Go to your [Stripe Test Dashboard > Payments](https://dashboard.stripe.com/test/payments).
    *   You should see a new Payment Intent created corresponding to the test order. Check its status (e.g., `Requires capture`, `Succeeded`, `Failed`).
    *   Check [Stripe Test Dashboard > Developers > Events](https://dashboard.stripe.com/test/events) and [Logs](https://dashboard.stripe.com/test/logs) for detailed API interactions.
    *   Check [Stripe Test Dashboard > Developers > Webhooks](https://dashboard.stripe.com/test/webhooks) and click your endpoint to see if Stripe successfully sent events (look for `200 OK` responses).

8.  **Verify Database (Optional):**
    *   You can connect to the `payment-db` container and check the payments table:
        ```bash
        docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "SELECT id, payment_id, order_id, status FROM payments;"
        ```

9.  **Verify Kafka Messages (Optional):**
    *   Check the messages in the payment_events topic:
        ```bash
        docker exec -it campusg-kafka-1 kafka-console-consumer --bootstrap-server kafka:9092 --topic payment_events --from-beginning
        ```

By following these steps, you can verify that the Payment Service correctly processes payment authorization requests triggered by the saga, interacts with Stripe, handles webhooks, and communicates the results back via Kafka.

## Troubleshooting

### Flask Application Context Errors
If you see errors like "Working outside of application context," ensure the fix in `app/services/kafka_service.py` is properly applied and the Flask app instance is being passed correctly in `app/__init__.py`.

### Database Schema Errors
If you encounter "column payments.id does not exist" errors, you may need to drop and recreate the payments table:
```bash
docker exec -it campusg-payment-db-1 psql -U postgres -d payment_db -c "DROP TABLE IF EXISTS payments CASCADE;"
docker restart campusg-payment-service-1
```

### Kafka Connection Issues
If Kafka connectivity issues occur, check logs with:
```bash
docker logs campusg-payment-service-1 | grep Kafka
```
Ensure Kafka is running and the bootstrap servers configuration is correct.
