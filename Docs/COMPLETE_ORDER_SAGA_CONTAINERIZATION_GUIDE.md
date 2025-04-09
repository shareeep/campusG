# Complete Order Saga Containerization and Temporal Integration Guide

This guide outlines the steps to containerize the `complete-order-saga-orchestrator` service and integrate the Temporal server stack directly into the main `docker-compose.yml`. This allows running the entire application, including Temporal, with a single `docker-compose up` command.

## Prerequisites

*   Docker and Docker Compose installed.
*   A `.env` file in the project root defining necessary environment variables (e.g., `STRIPE_SECRET_KEY`, `CLERK_SECRET_KEY`, potentially Temporal image versions like `POSTGRESQL_VERSION`, `TEMPORAL_VERSION`).

## Steps

1.  [X] **Code Cleanup:**
    *   [X] Remove database-related code from `services/complete-order-saga-orchestrator/config.py`.
    *   [X] Simplify/remove unused code in `services/complete-order-saga-orchestrator/app.py`.
    *   [X] Modify `services/complete-order-saga-orchestrator/api_trigger.py` to read `TEMPORAL_GRPC_ENDPOINT` from environment variables.
    *   [X] Modify `services/complete-order-saga-orchestrator/worker.py` to read `TEMPORAL_GRPC_ENDPOINT` from environment variables.
    *   [X] Modify `services/complete-order-saga-orchestrator/activities.py` to read service URLs (`*_SERVICE_URL`) and `KAFKA_BROKERS` from environment variables.

2.  [X] **Modify Dockerfile:**
    *   [X] Remove the `CMD` instruction from `services/complete-order-saga-orchestrator/Dockerfile`.

3.  [X] **Modify `docker-compose.yml` (Main Project):**
    *   [X] Remove the `complete-order-saga-db` service definition.
    *   [X] Remove the `complete_order_saga_db_data` volume definition.
    *   [X] Add Temporal services (`temporal-db`, `temporal`, `temporal-ui`, `temporal-admin-tools`) from `temporal/docker-compose-postgres.yml`.
    *   [X] Adjust Temporal services to use the `default` network and depend on `temporal-db`.
    *   [X] Adjust Temporal service volume paths (e.g., `./temporal/dynamicconfig`).
    *   [X] Add `temporal_db_data` named volume.
    *   [X] Rename the existing `complete-order-saga-orchestrator` service to `complete-order-saga-api`.
    *   [X] Update the `complete-order-saga-api` service:
        *   Set `container_name: complete-order-saga-api`.
        *   Add `command: python api_trigger.py`.
        *   Update `ports` mapping (e.g., `3103:5000`).
        *   Update `environment` variables (remove `DATABASE_URL`, set `TEMPORAL_GRPC_ENDPOINT=temporal:7233`, `*_SERVICE_URL`s, `KAFKA_BROKERS`).
        *   Update `depends_on` (add `temporal`, remove `complete-order-saga-db`).
        *   Update `networks` (remove `temporal-net`, ensure `default`).
    *   [X] Add a new `complete-order-saga-worker` service:
        *   Use the same `build` context.
        *   Set `container_name: complete-order-saga-worker`.
        *   Add `command: python worker.py`.
        *   Set `environment` variables (same as API, without `DATABASE_URL`).
        *   Update `depends_on` (add `temporal`, remove `complete-order-saga-db`).
        *   Update `networks` (remove `temporal-net`, ensure `default`).
    *   [X] Remove the external `temporal-net` network definition.

4.  [ ] **Testing:**
    *   Start the integrated application stack: `docker-compose up -d --build`
    *   Verify all containers are running (`docker ps`), including `temporal`, `temporal-ui`, `complete-order-saga-api`, `complete-order-saga-worker`, etc.
    *   Check logs for `temporal`, `complete-order-saga-api`, and `complete-order-saga-worker` for errors.
    *   Access the Temporal UI (usually `http://localhost:8080`).
    *   Test triggering the saga via the API (likely `http://localhost:3103/triggerCompleteOrderWorkflow`) and observe the workflow in the Temporal UI.
