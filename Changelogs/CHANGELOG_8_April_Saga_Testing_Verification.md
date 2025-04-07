# Changelog - April 8, 2025: Saga Rollback & Cancellation - Testing & Verification

This document summarizes the testing performed on the recently implemented rollback (compensation) and cancellation features for the Create Order Saga, outlines how to test them, and notes missing functionality for final state transitions.

## Summary of Implemented Features:

*   **Rollback/Compensation:** The orchestrator now attempts to undo previous actions (cancel order, revert payment) if a step fails before the order is finalized. Saga status enters `COMPENSATING`.
*   **Auto-Cancellation:** A background job polls an external Timer Service and initiates cancellation if a timer is found with status `"Expired"`.
*   **Manual Cancellation:** An API endpoint (`POST /sagas/{saga_id}/cancel`) allows triggering cancellation manually.
*   **Unified Cancellation:** Both auto and manual cancellation trigger calls to cancel the external timer, cancel the order via Kafka command (`cancel_order`), and revert payment via Kafka command (`revert_payment`) if applicable. Saga status enters `CANCELLING`.

## Testing Performed (Summary):

*   **Scenario 1b (Rollback on Order Status Update Failure):**
    *   **Setup:** Temporarily modified the Order Service (`handle_update_order_status_command`) to simulate a failure after receiving the command. Rebuilt and restarted the `order-service`.
    *   **Execution:** Triggered a new saga via `POST /orders`.
    *   **Observation (Orchestrator Logs & Saga Status):** Verified that the orchestrator received the `order.status_update_failed` event, initiated compensation, published the `revert_payment` command, and set the saga status to `COMPENSATING`.
    *   **Result:** This test **successfully verified** the compensation trigger and initiation logic for this failure scenario.

*   **Scenario 2 (Manual Cancellation):**
    *   **Status:** This scenario has **not yet been explicitly tested** by triggering the `POST /sagas/{saga_id}/cancel` endpoint after the implementation.

## Current Status & Next Steps:

*   The core logic for initiating compensation (`COMPENSATING` state) and cancellation (`CANCELLING` state) is implemented and partially verified (Scenario 1b).
*   **Missing Functionality:** The orchestrator currently **lacks event handlers** for the confirmation events that signal the completion of compensation or cancellation actions. Specifically, it does not yet handle:
    *   `payment.reverted` (or `payment.released` as currently published by Payment Service)
    *   `order.cancelled` (published by Order Service)
*   **Impact:** Because these confirmation events are not handled, the saga state remains `COMPENSATING` or `CANCELLING` even after the underlying services have successfully completed the rollback/cancellation actions.
*   **To Achieve Final States (`COMPENSATED`/`CANCELLED`):** Event handlers for `payment.reverted` (or `payment.released`) and `order.cancelled` need to be added to the `CreateOrderSagaOrchestrator`. These handlers would check if all necessary compensating/cancellation actions for that saga have been confirmed and then update the saga status to the final `COMPENSATED` or `CANCELLED` state respectively.

---

## Manual Testing Instructions (as of April 8, 2025)

**Prerequisites:**

*   Ensure all services are running (`docker compose up`).
*   Ensure the user `user_2vP0EpVyQDOVklQ1SDDheOGao7W` exists with a valid payment method linked via the frontend UI or previous setup.

**Scenario 1b: Testing Rollback on Order Status Update Failure**

*   **Purpose:** Verify compensation (payment revert) when `update_order_status` fails after payment succeeds.
*   **Setup:**
    1.  Temporarily modify `services/order_service/app/services/kafka_service.py`: Inside the `handle_update_order_status_command` function, add the line `raise Exception("Simulating status update failure")` before the `db.session.commit()` line.
    2.  Rebuild and restart the Order Service: `docker compose up -d --build order-service`
*   **Execution:**
    1.  Trigger the saga (note the `saga_id`):
        ```bash
        curl -X POST http://localhost:3101/orders -H "Content-Type: application/json" -d '{ "customer_id": "user_2vP0EpVyQDOVklQ1SDDheOGao7W", "order_details": { "foodItems": [ {"item_name": "Status Fail Test", "price": 12.00, "quantity": 1} ], "deliveryLocation": "Test Location Status Fail" } }'
        ```
*   **Verification:**
    1.  Monitor Orchestrator Logs (`docker logs campusg-create-order-saga-orchestrator-1 --tail 150`): Look for `order.status_update_failed` event received, followed by `Initiating compensation... Reverting payment...`, and `Published command revert_payment...`.
    2.  Check Saga Status (`curl http://localhost:3101/sagas/<saga_id>`): Verify the status is `COMPENSATING`.
*   **Cleanup:**
    1.  **CRITICAL:** Remove the `raise Exception(...)` line from `services/order_service/app/services/kafka_service.py`.
    2.  Rebuild and restart the Order Service: `docker compose up -d --build order-service`

**Scenario 2: Testing Manual Cancellation**

*   **Purpose:** Verify the `POST /sagas/{saga_id}/cancel` endpoint initiates cancellation.
*   **Execution:**
    1.  Trigger the saga (note the `saga_id`):
        ```bash
        curl -X POST http://localhost:3101/orders -H "Content-Type: application/json" -d '{ "customer_id": "user_2vP0EpVyQDOVklQ1SDDheOGao7W", "order_details": { "foodItems": [ { "item_name": "McSpicy Meal", "price": 9.80, "quantity": 1 }, { "item_name": "Iced Milo", "price": 3.50, "quantity": 2 } ], "deliveryLocation": "SMU SCIS L2 Study Area" } }'
        ```
    2.  Wait a few seconds for the saga to progress (e.g., past payment authorization).
    3.  Request cancellation (replace `<saga_id>`):
        ```bash
        curl -X POST http://localhost:3101/sagas/<saga_id>/cancel
        ```
        *(Expect `202 Accepted` response)*
*   **Verification:**
    1.  Monitor Orchestrator Logs (`docker logs campusg-create-order-saga-orchestrator-1 --tail 150`): Look for `Received request to cancel saga...`, `Initiating cancellation...`, `Requesting external timer cancellation...`, `Publishing cancel_order command...`, `Publishing revert_payment command...`.
    2.  Check Saga Status (`curl http://localhost:3101/sagas/<saga_id>`): Verify the status is `CANCELLING`.

**Scenario 3: Observing Auto-Cancellation Polling**

*   **Purpose:** Verify the background polling job is running. (Full auto-cancellation requires controlling the external timer service).
*   **Verification:**
    1.  Check Orchestrator startup logs (`docker logs campusg-create-order-saga-orchestrator-1`): Look for `Started background scheduler...`.
    2.  Check Orchestrator logs periodically (`docker logs campusg-create-order-saga-orchestrator-1 --tail 50`): Look for `Polling for expired timers...` messages every ~60 seconds.
