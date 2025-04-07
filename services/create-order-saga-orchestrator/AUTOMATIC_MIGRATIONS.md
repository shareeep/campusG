# Automatic Database Migrations for Create Order Saga

## Overview

The Create Order Saga Orchestrator service now includes automatic database schema setup and migrations. When the service starts, it will:

1. Wait for the PostgreSQL database to be available (with retries)
2. Automatically run all pending migrations
3. Create the required database schema (tables, ENUMs, and triggers)

## Implementation Details

### Database Schema

The schema includes:

- **ENUM Types**:
  - `sagastatus`: STARTED, COMPLETED, FAILED, COMPENSATING, COMPENSATED
  - `sagastep`: GET_USER_DATA, CREATE_ORDER, AUTHORIZE_PAYMENT, HOLD_FUNDS, UPDATE_ORDER_STATUS, START_TIMER, NOTIFY_USER

- **Tables**:
  - `create_order_saga_states`: Tracks the state of each create order saga instance

- **Trigger**:
  - Automatically updates the `updated_at` timestamp column when records are updated

### Migration Files

The migration system uses Flask-Migrate and Alembic to manage database schema changes:

- `migrations/alembic.ini`: Alembic configuration
- `migrations/env.py`: Environment setup for migrations
- `migrations/versions/001_initial_schema.py`: Initial schema setup

### Startup Process

The service's startup process has been updated in `run.py` to:

1. Connect to PostgreSQL with retry logic
2. Run all pending migrations automatically
3. Start the Flask application if database setup is successful

In Docker, the command has been changed from using the Flask CLI to directly running the Python script:
```
CMD ["python", "run.py"]
```

## Testing

To test the automatic migrations:

1. Start the services with Docker Compose:
   ```
   docker-compose up -d
   ```

2. Check the logs to verify migrations ran successfully:
   ```
   docker logs campusg-order-saga-orchestrator-1
   ```

## Troubleshooting

If migrations fail to run:

1. Check database connectivity and credentials
2. Inspect the logs for specific error messages
3. Ensure the migrations directory is properly mounted in the container
4. Try running migrations manually inside the container:
   ```
   docker exec -it campusg-order-saga-orchestrator-1 flask db upgrade
