# Changelog - April 3, 2025

## Fixes

*   **Resolved Docker Health Check Failures for Multiple Services:**
    *   **Issue:** The `timer-service`, `order-service`, `notification-service`, and `create-order-saga-orchestrator` were consistently marked as unhealthy by Docker Compose after starting.
    *   **Root Cause:** The health check defined in `docker-compose.yml` for these services uses the `curl` command to check the `/health` endpoint. However, the `curl` utility was missing from the base `python:3.11-slim` Docker image used by these services.
    *   **Fix:** Modified the `Dockerfile` for each of the affected services (`timer-service`, `order-service`, `notification-service`, `create-order-saga-orchestrator`) to install `curl` using `apt-get` during the image build process.
    *   **Result:** With `curl` available in the container images, the health checks now pass successfully, and the services are correctly reported as healthy by Docker Compose.
