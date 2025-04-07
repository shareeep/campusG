# Changelog - April 7, 2025: Create Order Saga Enhancements (Rollback & Cancellation)

This update introduces significant improvements to the Create Order Saga orchestrator, adding robustness through compensation (rollback) logic and providing mechanisms for order cancellation.

## Key Changes (Simplified View):

1.  **Compensation (Rollback) Logic:**
    *   The saga now attempts to automatically undo previous steps if a later step fails *before* the order is finalized (status set to `CREATED`).
    *   **How it works:** If payment fails after the order was created, the saga tries to cancel the order. If updating the order status fails after payment succeeded, the saga tries to revert the payment.
    *   This helps maintain data consistency. The saga status is set to `COMPENSATING` during rollback.

2.  **Auto-Cancellation (30-Minute Timer):**
    *   A background task now runs periodically (e.g., every minute).
    *   **How it works:** It checks an external Timer Service API. If the API shows a timer for an active saga is `"Expired"`, the orchestrator automatically starts the cancellation flow.

3.  **Manual Cancellation:**
    *   A new API endpoint `POST /sagas/{saga_id}/cancel` is available.
    *   **How it works:** Allows external systems (like UI) to request cancellation of an order still in progress.

4.  **Unified Cancellation Flow:**
    *   Both auto and manual cancellations trigger the same process:
        *   Tell the external Timer Service to cancel its timer.
        *   Tell the Order Service to mark the order as `CANCELLED`.
        *   Tell the Payment Service to revert the payment (if it was authorized).
    *   The saga status is set to `CANCELLING` during this process.

## Technical Details:

*   **Compensation Trigger:** Implemented within the failure event handlers (`handle_payment_info_failed`, `handle_payment_failed`, `handle_order_status_update_failed`) in `saga_orchestrator.py`. These handlers now check the current `saga_state` (specifically `order_id` and `payment_id`) to determine which compensating actions are necessary.
    *   `handle_payment_info_failed`: If `saga_state.order_id` exists, publishes `cancel_order` command.
    *   `handle_payment_failed`: If `saga_state.order_id` exists, publishes `cancel_order` command.
    *   `handle_order_status_update_failed`: If `saga_state.payment_id` exists, publishes `revert_payment` command.
    *   The saga status is set to `SagaStatus.COMPENSATING`.

*   **Auto-Cancellation Implementation:**
    *   Uses `APScheduler` integrated via `app/__init__.py` to periodically call `_poll_for_cancellations` in `saga_orchestrator.py`.
    *   `_poll_for_cancellations` calls `http_client.get_timers_for_cancellation()`.
    *   It iterates through the response, filtering for timers with `"Status": "Expired"`.
    *   For each expired timer, it finds the corresponding `CreateOrderSagaState` (using `SagaId` or `OrderId`).
    *   If the saga is found and its status is `STARTED`, it calls `_initiate_cancellation(saga_state, reason="Order timed out (30 minutes)")`.

*   **Manual Cancellation Implementation:**
    *   A new Flask route `POST /sagas/<string:saga_id>/cancel` is defined in `app/api/routes.py`.
    *   The route handler retrieves the `CreateOrderSagaState` by `saga_id`.
    *   It checks if `saga_state.status` is `STARTED` or `COMPENSATING` (allowing cancellation if stuck compensating).
    *   If valid, it calls `orchestrator._initiate_cancellation(saga_state, reason="Manual cancellation requested by user")`.
    *   Returns `202 Accepted` if initiation is successful, `409 Conflict` if not in a cancellable state, `404 Not Found`, or `500 Internal Server Error`.

*   **`_initiate_cancellation` Method (`saga_orchestrator.py`):**
    *   Checks if the saga is already in a final or cancelling state.
    *   Sets `saga_state.status` to `SagaStatus.CANCELLING`.
    *   Calls `http_client.cancel_timer(saga_state.order_id)` (logs warning on failure but continues).
    *   If `saga_state.order_id` exists, publishes `cancel_order` command via Kafka.
    *   If `saga_state.payment_id` exists, publishes `revert_payment` command via Kafka.
    *   Currently, the saga remains in `CANCELLING` state after publishing commands. Further logic could be added to handle `order.cancelled` and `payment.reverted` events to transition to `CANCELLED` or `COMPENSATED` state upon confirmation.

## Affected Files:

*   **`services/create-order-saga-orchestrator/`**:
    *   `app/models/saga_state.py`: Added `CANCELLING`, `CANCELLED` statuses; added `payment_id` field.
    *   `app/services/saga_orchestrator.py`: Added compensation logic, `_initiate_cancellation`, `_poll_for_cancellations`, scheduler methods. Updated `handle_payment_authorized`.
    *   `app/services/kafka_service.py`: Added `publish_cancel_order_command`, `publish_revert_payment_command`.
    *   `app/services/http_client.py`: Added `get_timers_for_cancellation`, `cancel_timer`.
    *   `app/api/routes.py`: Added `POST /sagas/{saga_id}/cancel` endpoint.
    *   `app/__init__.py`: Added `APScheduler` integration and `atexit` shutdown hook.
    *   `requirements.txt`: Added `APScheduler==3.10.4`.
*   **`services/order_service/`**:
    *   `app/services/kafka_service.py`: Added `handle_cancel_order_command`, `publish_order_cancelled_event`.
