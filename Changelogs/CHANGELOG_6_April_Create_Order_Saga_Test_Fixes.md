# Changelog - April 6, 2025: Create Order Saga End-to-End Test & Fixes

**Goal:** Perform a step-by-step test of the Create Order Saga, simulating the initial UI request and verifying the flow through all microservices.

**Testing Approach:**
Initiated the saga by sending an HTTP POST request to the Create Order Saga Orchestrator (`/api/orders` endpoint), simulating a UI action. Monitored service logs (`docker logs`) at each step to verify expected behavior and Kafka message flow.

**How to Reproduce End-to-End Test:**

1.  **Prerequisites:**
    *   Ensure all services (`docker compose up`) are running and healthy.
    *   Ensure a test user exists (e.g., `clerk_user_id: 'test_customer'`) with a valid Stripe Customer ID and a default payment method (`pm_card_visa` can be used for testing). If not, create/update the user using the User Service API:
        *   Create user (simulating Clerk webhook):
            ```bash
            curl -X POST http://localhost:3001/api/webhook/clerk -H "Content-Type: application/json" -d '{ "type": "user.created", "data": { "id": "test_customer", "email_addresses": [{"email_address": "test_customer@example.com", "id": "idn_test", "linked_to": [], "object": "email_address", "verification": null}], "first_name": "Test", "last_name": "Customer", "phone_numbers": [], "username": "testcustomer", "created_at": '$(date +%s)', "updated_at": '$(date +%s)' } }'
            ```
        *   Add test payment method:
            ```bash
            curl -X PUT http://localhost:3001/api/user/test_customer/payment -H "Content-Type: application/json" -d '{ "paymentMethodId": "pm_card_visa" }'
            ```

2.  **Trigger Saga:** Send the initial POST request to the orchestrator (replace details as needed):
    ```bash
    curl -X POST http://localhost:3101/orders -H "Content-Type: application/json" -d '{ "customer_id": "test_customer", "order_details": { "foodItems": [ {"item_name": "Test Item", "price": 15.50, "quantity": 1} ], "deliveryLocation": "Test Location" } }'
    ```
    *   Note the `saga_id` returned in the JSON response (e.g., `"saga_id":"..."`).

3.  **Monitor Logs (Optional):** Check the logs of each service (`docker logs <container_name> --tail 50`) to observe the flow:
    *   `campusg-create-order-saga-orchestrator-1`
    *   `campusg-order-service-1`
    *   `campusg-user-service-1`
    *   `campusg-payment-service-1`
    *   `campusg-timer-service-1`

4.  **Poll for Status:** After a few seconds, simulate the UI polling for the final status using the `saga_id` noted in step 2:
    ```bash
    # Replace <saga_id> with the actual ID from the POST response
    curl http://localhost:3101/sagas/<saga_id>
    ```
    *   Check the response for `"status":"COMPLETED"`.

**Debugging Steps & Fixes:**

1.  **Initial Trigger:** Sent HTTP POST to orchestrator.
    *   **Result:** Saga started successfully, orchestrator published `create_order` command.

2.  **Order Service (`create_order` handler):**
    *   **Issue:** Logs showed no processing of the `create_order` command. Investigation revealed the Kafka consumer wasn't initialized and the command handler wasn't registered in `app/__init__.py` or `run.py`.
    *   **Fix 1:** Added `handle_create_order_command` function to `services/order_service/app/services/kafka_service.py`.
    *   **Fix 2:** Registered the handler in the `init_kafka` function within `services/order_service/app/services/kafka_service.py`.
    *   **Issue:** Rebuild failed due to circular import (`kafka_service` -> `routes` -> `kafka_service`).
    *   **Fix 3:** Created `services/order_service/app/utils/calculations.py` and moved shared calculation functions there. Updated imports in `kafka_service.py` and `api/routes.py`.
    *   **Issue:** Order creation failed with `TypeError: 'saga_id' is an invalid keyword argument for Order`. The `Order` model was missing the `saga_id` column.
    *   **Fix 4:** Added `saga_id` column definition to `Order` model in `services/order_service/app/models/models.py`.
    *   **Fix 5:** Added the `saga_id` column to the `orders` table in the `order-db` database using `ALTER TABLE orders ADD COLUMN saga_id VARCHAR(36);`.
    *   **Result:** Order Service successfully processed `create_order`, created the order in the DB, and published `order.created` event.

3.  **Orchestrator (`order.created` handler):**
    *   **Result:** Successfully received `order.created` event and published `get_payment_info` command.

4.  **User Service (`get_payment_info` handler):**
    *   **Issue:** Logs showed "Unhandled message type received: get_payment_info". The handler was checking for `get_user_payment_info` instead.
    *   **Fix 1:** Corrected the `if` condition in `process_message` within `services/user-service/app/services/kafka_service.py` to check for `get_payment_info`. Also adjusted payload extraction logic to match what the orchestrator sends (`user_id`).
    *   **Issue:** Handler failed with "User not found" for `test_customer`.
    *   **Fix 2:** Created the `test_customer` user by simulating a Clerk webhook event via `curl -X POST http://localhost:3001/api/webhook/clerk ...`. This also created the Stripe customer ID.
    *   **Issue:** Handler failed with "Default payment method not set for user".
    *   **Fix 3:** Added a test payment method (`pm_card_visa`) to the user via `curl -X PUT http://localhost:3001/api/user/test_customer/payment ...`.
    *   **Result:** User Service successfully processed `get_payment_info` and published `user.payment_info_retrieved` event.

5.  **Orchestrator (`user.payment_info_retrieved` handler):**
    *   **Result:** Successfully received `user.payment_info_retrieved` event and published `authorize_payment` command.

6.  **Payment Service (`authorize_payment` handler):**
    *   **Issue:** Service failed to start due to `entrypoint.sh` errors (`sleep: invalid time interval ‘5\r’`, `Syntax error: end of file unexpected`). This was caused by Windows line endings (CRLF) being used instead of Unix (LF), likely due to the volume mount overwriting the file fixed by `dos2unix` in the Dockerfile.
    *   **Fix 1:** Removed the volume mount for `payment-service` in `docker-compose.yml` to force usage of the image's entrypoint script.
    *   **Issue:** Handler failed, publishing `payment.failed` with error `INVALID_PAYLOAD`. The payload structure sent by the orchestrator didn't match what the Payment Service expected (key names, nesting, amount format).
    *   **Fix 2:** Modified the `handle_payment_info_retrieved` function in `services/create-order-saga-orchestrator/app/services/saga_orchestrator.py` to construct the `authorize_payment` payload correctly (using `customer` and `order` keys, nesting payment info, sending amount in cents).
    *   **Issue:** Handler failed with Stripe API error `InvalidRequestError: ... you must provide a return_url ...`.
    *   **Fix 3:** Modified the `handle_authorize_payment_command` in `services/payment-service/app/services/stripe_service.py` to add `'automatic_payment_methods': {'enabled': True, 'allow_redirects': 'never'}` to the `stripe.PaymentIntent.create` call.
    *   **Result:** Payment Service successfully processed `authorize_payment`, created the Stripe PaymentIntent, and published `payment.authorized` event.

7.  **Orchestrator (`payment.authorized` handler):**
    *   **Result:** Successfully received `payment.authorized` event and published `update_order_status` command.

8.  **Order Service (`update_order_status` handler):**
    *   **Issue:** Logs showed "No handler registered for command type: update_order_status".
    *   **Fix 1:** Added `handle_update_order_status_command` function to `services/order_service/app/services/kafka_service.py`.
    *   **Fix 2:** Registered the handler in the `init_kafka` function within the same file.
    *   **Issue:** Handler failed with `NameError: name 'timezone' is not defined`.
    *   **Fix 3:** Added `from datetime import timezone` import to `services/order_service/app/services/kafka_service.py`.
    *   **Issue:** Orchestrator didn't process the next step because Order Service published `order.updated` instead of the expected `order.status_updated`.
    *   **Fix 4:** Changed the event type published in `handle_update_order_status_command` to `order.status_updated`.
    *   **Result:** Order Service successfully processed `update_order_status`, updated the order status to `CREATED`, and published `order.status_updated` event.

9.  **Orchestrator (`order.status_updated` handler):**
    *   **Result:** Successfully received `order.status_updated`. Attempted HTTP call to Timer Service (failed with 404 as expected), fell back to Kafka, and published `start_order_timer` command.

10. **Timer Service (`start_order_timer` handler):**
    *   **Issue:** Service logs showed no Kafka consumer activity. The `kafka_service.py` only contained a Producer.
    *   **Fix 1:** Rewrote `services/timer-service/app/services/kafka_service.py` to include `KafkaConsumer` setup, consumer loop, handler registration (`init_kafka`), and the `handle_start_order_timer` function (publishing `timer.started` immediately as a placeholder).
    *   **Issue:** Logs still showed no Kafka activity, indicating `init_kafka` wasn't running or logs were suppressed.
    *   **Fix 2:** Added explicit `print()` and `logger.setLevel(logging.INFO)` calls to `services/timer-service/app/services/kafka_service.py` for diagnostics. Confirmed `init_kafka` was called.
    *   **Result:** Timer Service successfully received `start_order_timer` command and published the placeholder `timer.started` event.

11. **Orchestrator (`timer.started` handler):**
    *   **Result:** Successfully received `timer.started` event and marked the saga as COMPLETED.

**Conclusion:** The Create Order Saga flow was successfully tested end-to-end after applying numerous fixes across the Orchestrator, Order Service, User Service, Payment Service, and Timer Service, primarily related to Kafka handler registration, payload consistency, database schema, and service configuration (line endings, volume mounts).
