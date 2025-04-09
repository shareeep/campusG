# Accept Order Saga Orchestrator (Temporal)

## Overview

This service orchestrates the "Accept Order" workflow using the Temporal workflow engine. It is triggered by an API call when a runner accepts an order and coordinates the necessary steps across different services via Temporal activities.

## Architecture

- **Workflow Engine:** Temporal.io
- **Trigger:** Flask API endpoint (`api_trigger.py`)
- **Workflow Definition:** Defines the sequence of steps and compensation logic (`workflow.py`).
- **Activities:** Implement interactions with external services (primarily via HTTP calls) (`activities.py`).
- **Worker:** Executes workflow and activity tasks (`worker.py`).

## Sequence of Steps (Workflow Logic)

1.  **Verify and Accept Order:** Calls the Order Service via HTTP POST to `/verifyAndAcceptOrder` to assign the runner and update the order status to `ACCEPTED`.
2.  **Notify Timer Service:** Calls the Timer Service via HTTP POST (URL from `TIMER_SERVICE_URL` env var) to stop the initial order acceptance timer.

## Compensation Logic

- If `notify_timer_service` fails, the workflow compensates by calling the `revert_order_status` activity.
- **`revert_order_status` Activity:** Calls the Order Service via HTTP POST to `/clearRunner` to remove the assigned runner and revert the order status (likely back to `CREATED`).

## HTTP API Endpoints (`api_trigger.py`)

*   **`POST /acceptOrder`**:
    *   **Purpose:** Triggers the start of a new `AcceptOrderWorkflow` instance in Temporal.
    *   **Request Body:** `{ "order_id": "string", "runner_id": "string" }` (Required)
    *   **Response (Success):** `200 OK` - `{ "message": "Workflow triggered", "workflow_id": "temporal-workflow-id" }`
    *   **Response (Failure):** `400 Bad Request`, `500 Internal Server Error` (if workflow fails to start)

*   **`GET /health`**:
    *   **Purpose:** Basic health check for the Flask API trigger service.
    *   **Response:** `{'status': 'healthy'}`

## Kafka Interactions

- **None directly observed.** This orchestrator primarily uses **HTTP calls** within its Temporal activities (`activities.py`) to communicate with the Order Service and Timer Service. Kafka libraries might be present but don't appear to be used for the core orchestration logic in this service.

## Setup & Running

1.  **Temporal Server:** Requires a running Temporal server instance.
2.  **Environment Variables:**
    *   `TEMPORAL_GRPC_ENDPOINT`: Address of the Temporal frontend service (e.g., `localhost:7233`).
    *   `ORDER_SERVICE_URL`: Base URL for the Order Service (e.g., `http://order-service:3002`).
    *   `TIMER_SERVICE_URL`: Full URL for the Timer Service's stop timer endpoint.
3.  **Run Worker:** Start the Temporal worker process (`worker.py`) which listens for tasks on the `accept-order-task-queue`.
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

- `workflow.py`: Defines the `AcceptOrderWorkflow` logic using Temporal's Python SDK.
- `activities.py`: Defines activities (`verify_and_accept_order`, `notify_timer_service`, `revert_order_status`) that interact with external services via HTTP.
- `worker.py`: Runs the Temporal worker to execute workflow and activity tasks.
- `api_trigger.py`: Flask application that exposes the `/acceptOrder` endpoint to start the workflow.
- `requirements.txt`: Lists dependencies, including `temporalio`.
