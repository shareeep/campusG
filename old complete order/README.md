# Complete Order Saga Orchestrator

The Complete Order Saga Orchestrator is responsible for managing the workflow of completing an order when a runner marks it as delivered. This service orchestrates the following steps:

1. Update order status to DELIVERED
2. Retrieve runner payment information
3. Release funds to the runner via Payment Service
4. Update order status to COMPLETED

## Setup and Configuration

### Prerequisites

- Docker and Docker Compose
- PostgreSQL
- Kafka
- Payment Service
- Order Service
- User Service

### Environment Variables

The following environment variables can be configured:

- `DATABASE_URL`: PostgreSQL connection URL (default: `postgresql://postgres:postgres@localhost:5432/complete_order_saga_db`)
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers (default: `kafka:9092`)
- `ORDER_SERVICE_URL`: Order service URL (default: `http://localhost:3002`)
- `PAYMENT_SERVICE_URL`: Payment service URL (default: `http://localhost:3003`)
- `USER_SERVICE_URL`: User service URL (default: `http://localhost:3001`)

## Database Initialization

The service uses Flask-Migrate for database migrations. When running in Docker, the entrypoint script will automatically run migrations before starting the application.

To manually initialize the database:

```bash
# Initialize the migration repository (only needed once)
flask db init

# Generate a migration
flask db migrate -m "Initial migration"

# Apply migrations
flask db upgrade
```

## Testing the Complete Order Saga

### Running with Docker Compose

1. Start all services:

```bash
docker-compose up -d
```

2. Test the saga using the provided test script:

```bash
# With an existing order ID
python services/complete-order-saga-orchestrator/test_complete_order.py your-order-id

# Or let the script generate a random order ID
python services/complete-order-saga-orchestrator/test_complete_order.py
```

### Manual Testing

1. Trigger the complete order saga:

```bash
curl -X POST http://localhost:3000/saga/complete/completeOrder \
  -H "Content-Type: application/json" \
  -d '{"orderId": "your-order-id"}'
```

2. Monitor the saga state:

```bash
# Replace saga-id with the ID from the previous response
curl -N http://localhost:3000/saga/complete/orderUpdateStream/saga-id
```

### Monitoring Kafka Messages

To monitor Kafka messages during testing:

```bash
# Monitor command messages
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic complete_order_commands --from-beginning

# Monitor event messages
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic complete_order_events --from-beginning
```

## Troubleshooting

### Database Issues

If you encounter database connection issues:

1. Ensure PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Create the database if it doesn't exist:
   ```bash
   docker-compose exec postgres psql -U postgres -c "CREATE DATABASE complete_order_saga_db;"
   ```

3. Run migrations manually:
   ```bash
   docker-compose exec complete-order-saga-orchestrator flask db upgrade
   ```

### Kafka Issues

If Kafka connectivity is problematic:

1. Check if Kafka is running:
   ```bash
   docker-compose ps kafka zookeeper
   ```

2. Verify topics exist:
   ```bash
   docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
   ```

3. Create missing topics:
   ```bash
   docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic complete_order_commands --partitions 1 --replication-factor 1
   docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic complete_order_events --partitions 1 --replication-factor 1
   ```

## Current Implementation Notes

The current implementation includes a temporary stub for the "release funds" functionality in the payment service. This stub always returns a successful response to allow testing of the complete saga flow while the actual payment processing implementation is being developed in a separate branch.
