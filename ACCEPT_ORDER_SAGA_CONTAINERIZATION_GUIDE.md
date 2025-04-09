# Accept Order Saga Containerization Guide

This guide outlines the steps to containerize the `accept-order-saga-orchestrator` service using Docker Compose, allowing it to run both its API trigger and Temporal worker components within the integrated Temporal setup.

**Key Differences from Complete Order Saga:**

*   **Missing Dependency:** The `temporalio` package was missing from `requirements.txt`.
*   **Port Mismatch:** The `api_trigger.py` script was configured to run on port 5000, while the Dockerfile exposed port 3000. This has been corrected to use port 3000 consistently.
*   **No Database Needed:** Analysis showed this saga does not require its own dedicated database (`accept-order-saga-db`), so it has been removed from the configuration.
*   **Entry Point:** The original Dockerfile used `run.py` (via `flask run`), but the actual API/Temporal logic resides in `api_trigger.py`. The setup now correctly uses `api_trigger.py` and `worker.py`.

## Prerequisites

*   Docker and Docker Compose installed.
*   The main CampusG `docker-compose.yml` defining other services (Kafka, User, Order, Notification) and the integrated Temporal stack.
*   A `.env` file in the project root defining necessary environment variables.

## Steps

1.  [ ] **Code Cleanup & Correction:**
    *   [ ] Add `temporalio` dependency to `services/accept-order-saga-orchestrator/requirements.txt`.
    *   [ ] Modify `services/accept-order-saga-orchestrator/api_trigger.py`:
        *   Read `TEMPORAL_GRPC_ENDPOINT` from environment variables.
        *   Ensure Flask runs on port 3000 (`app.run(host='0.0.0.0', port=3000)`).
        *   Add a `/health` endpoint.
    *   [ ] Modify `services/accept-order-saga-orchestrator/worker.py` to read `TEMPORAL_GRPC_ENDPOINT` from environment variables.
    *   [ ] Modify `services/accept-order-saga-orchestrator/activities.py` to read `ORDER_SERVICE_URL` from environment variables.
    *   [ ] (Optional) Remove unused `app/` directory and `run.py`.

2.  [ ] **Modify Dockerfile:**
    *   [ ] Remove the `CMD` instruction from `services/accept-order-saga-orchestrator/Dockerfile`.
    *   [ ] Remove `ENV FLASK_APP=run.py` from `services/accept-order-saga-orchestrator/Dockerfile`.

3.  [ ] **Modify `docker-compose.yml` (Main Project):**
    *   [ ] Remove the `accept-order-saga-db` service definition.
    *   [ ] Remove the `accept_order_saga_db_data` volume definition.
    *   [ ] Rename the existing `accept-order-saga-orchestrator` service to `campusg-accept-order-saga-api`.
    *   [ ] Update the `campusg-accept-order-saga-api` service:
        *   Set `command: python api_trigger.py`.
        *   Update `ports` mapping (e.g., `3102:3000`).
        *   Update `environment` variables (remove `DATABASE_URL`, `FLASK_APP`, `FLASK_DEBUG`; add `TEMPORAL_GRPC_ENDPOINT`, `ORDER_SERVICE_URL`, etc.).
        *   Update `depends_on` (add `temporal`, remove `accept-order-saga-db`).
        *   Add `healthcheck` for the `/health` endpoint on port 3000.
    *   [ ] Add a new `campusg-accept-order-saga-worker` service:
        *   Use the same `build` context.
        *   Set `container_name: campusg-accept-order-saga-worker`.
        *   Add `command: python worker.py`.
        *   Set `environment` variables (same as API, without DB/Flask vars).
        *   Set `depends_on` (add `temporal`, `order-service`, etc.).

4.  [ ] **Testing:**
    *   Start the integrated application stack: `docker-compose up -d --build`
    *   Verify containers are running (`docker ps`), including `campusg-accept-order-saga-api` and `campusg-accept-order-saga-worker`.
    *   Check logs for errors.
    *   Check API health: `http://localhost:3102/health`.
    *   Test triggering the saga via its API (POST to `http://localhost:3102/acceptOrder` with `{"order_id": "...", "runner_id": "..."}`) and observe the workflow in the Temporal UI (`http://localhost:8080`).
