# Complete Order Saga Orchestrator (Temporal)

## Overview

This service orchestrates the "Complete Order" workflow using the Temporal workflow engine. It is triggered by an API call when a runner confirms delivery and coordinates the final steps of an order, including updating status and releasing payment, via Temporal activities.

## Architecture

- **Workflow Engine:** Temporal.io
- **Trigger:** Flask API endpoint (`api_trigger.py`)
- **Workflow Definition:** Defines the sequence of steps and compensation logic (`workflows.py`).
- **Activities:** Implement interactions with external services via HTTP calls (`activities.py`).
- **Worker:** Executes workflow and activity tasks (`worker.py`).

## Sequence of Steps (Workflow Logic)

1.  **Update Order Status (to DELIVERED):** Calls the Order Service via HTTP POST to `/updateOrderStatus` to set the status to `DELIVERED`.
2.  **Get Runner Stripe Connect ID:** Calls the User Service via HTTP GET to `/api/user/<runner_id>/connect-account` to retrieve the runner's Stripe Connect account ID.
3.  **Get Payment ID:** Calls the Payment Service via HTTP GET to `/payment/<order_id>/status` to retrieve the internal `payment_id` associated with the order.
4.  **Release Funds:** Calls the Payment Service via HTTP POST to `/payment/<payment_id>/release`, providing the runner's Stripe Connect ID, to capture the payment and initiate the transfer to the runner.
5.  **Update Order Status (to COMPLETED):** Calls the Order Service via HTTP POST to `/updateOrderStatus` to set the final status to `COMPLETED`.

## Compensation Logic

- When `release_funds` fails, the workflow compensates by calling `rollback_release_funds`.
- **`rollback_release_funds` Activity:** Calls the Payment Service via HTTP POST to `/payment/<payment_id>/revert` to cancel/refund the payment.
- The service handles compensation for `update_order_status` activities through specific rollback mechanisms defined in the workflow.

## HTTP API Endpoints (`api_trigger.py`)

*   **`POST /triggerCompleteOrderWorkflow`**:
    *   **Purpose:** Triggers the start of a new `CompleteOrderWorkflow` instance in Temporal.
    *   **Request Body:** JSON object containing necessary details, including `order_id`, `runner_id`.
    *   **Response (Success):** `200 OK` - `{ "message": "Workflow triggered", "workflow_id": "temporal-workflow-id" }`
    *   **Response (Failure):** `500 Internal Server Error` (if workflow fails to start)

*   **`GET /health`**:
    *   **Purpose:** Basic health check for the Flask API trigger service.
    *   **Response:** `{'status': 'healthy'}`

## Kafka Interactions

- **No direct Kafka interactions.** This orchestrator exclusively uses **HTTP calls** within its Temporal activities (`activities.py`) to communicate with the Order Service, User Service, and Payment Service.

## Setup & Running

1.  **Temporal Server:** Requires a running Temporal server instance.
2.  **Environment Variables:**
    *   `TEMPORAL_GRPC_ENDPOINT`: Address of the Temporal frontend service (e.g., `localhost:7233`).
    *   `ORDER_SERVICE_URL`: Base URL for the Order Service (e.g., `http://order-service:3002`).
    *   `USER_SERVICE_URL`: Base URL for the User Service (e.g., `http://user-service:3001`).
    *   `PAYMENT_SERVICE_URL`: Base URL for the Payment Service (e.g., `http://payment-service:3003`).
3.  **Run Worker:** Start the Temporal worker process (`worker.py`) which listens for tasks on the `complete-order-queue`.
    ```bash
    # Example (adjust based on deployment)
    python worker.py
    ```
4.  **Run API Trigger:** Start the Flask API trigger service (`api_trigger.py`).
    ```bash
    # Example (adjust based on deployment)
    python api_trigger.py
    ```
    (Or use gunicorn in production)

## Key Files

- `workflows.py`: Defines the `CompleteOrderWorkflow` logic using Temporal's Python SDK.
- `activities.py`: Defines activities that interact with external services via HTTP.
- `worker.py`: Runs the Temporal worker to execute workflow and activity tasks.
- `api_trigger.py`: Flask application that exposes the `/triggerCompleteOrderWorkflow` endpoint.
- `requirements.txt`: Lists dependencies, including `temporalio`.
