# Create Order Saga Orchestrator

This microservice orchestrates the create order workflow, coordinating multiple services to complete the order creation business transaction. It implements the Saga pattern using Kafka for event-driven communication between services.

## Architecture

The Create Order Saga Orchestrator follows an event-driven architecture using Kafka for communication:

1. **Command Publishing**: The orchestrator publishes command messages to specific Kafka topics that each service listens to.
2. **Event Consumption**: The orchestrator listens to event topics where services publish the results of processing commands.
3. **State Management**: The orchestrator maintains the state of each saga instance in a PostgreSQL database.
4. **Compensation Handling**: If a step fails, the orchestrator initiates compensating actions to maintain data consistency.

## Sequence of Steps

The Create Order Saga follows these steps:

1. **Create Order**: Create an order record with status "pendingPayment" in the Order Service.
2. **Get User Payment Info**: Retrieve the customer's payment information from the User Service.
3. **Authorize Payment**: Process payment authorization via the Payment Service.
4. **Update Order Status**: Update the order status to "CREATED" in the Order Service.
5. **Start Timer**: Start a 30-minute timer in the Timer Service for runner acceptance.

## Kafka Topics

The orchestrator interacts with the following Kafka topics:

### Command Topics
- `order_commands`: Commands to the Order Service (create_order, update_order_status)
- `user_commands`: Commands to the User Service (get_payment_info)
- `payment_commands`: Commands to the Payment Service (authorize_payment)
- `timer_commands`: Commands to the Timer Service (start_order_timer)

### Event Topics
- `order_events`: Events from the Order Service (order.created, order.status_updated, order.creation_failed)
- `user_events`: Events from the User Service (user.payment_info_retrieved, user.payment_info_failed)
- `payment_events`: Events from the Payment Service (payment.authorized, payment.failed)
- `timer_events`: Events from the Timer Service (timer.started, timer.failed)

## API Endpoints

The service exposes the following Flask-based HTTP endpoints:

*   **`POST /orders`**:
    *   **Purpose:** Initiate a new create order saga.
    *   **Request Body:** `{ "customer_id": "string", "order_details": { "foodItems": [...], "deliveryLocation": "...", "deliveryFee": "..." } }`
    *   **Response (Success):** `202 Accepted` - `{ "success": true, "message": "Saga started successfully", "saga_id": "uuid", "status": "STARTED" }`
    *   **Response (Failure):** `400 Bad Request` or `500 Internal Server Error`

*   **`GET /sagas/<saga_id>`**:
    *   **Purpose:** Get the current state of a specific saga instance.
    *   **Path Parameter:** `saga_id` (string, UUID)
    *   **Response (Success):** `200 OK` - Complete saga state object (`id`, `status`, `current_step`, `order_id`, `error`, timestamps, etc.).
    *   **Response (Failure):** `404 Not Found`

*   **`GET /sagas`**:
    *   **Purpose:** List recent saga instances (limit 100).
    *   **Query Parameter:** `status` (string, e.g., `COMPLETED`, `FAILED`, `STARTED`) - Optional filter.
    *   **Response (Success):** `200 OK` - Array of summarized saga state objects.
    *   **Response (Failure):** `400 Bad Request` (for invalid status)

*   **`POST /sagas/<saga_id>/cancel`**:
    *   **Purpose:** Manually request cancellation/compensation for a specific saga instance.
    *   **Path Parameter:** `saga_id` (string, UUID)
    *   **Response (Success):** `202 Accepted` - `{ "message": "Saga cancellation initiated" }`
    *   **Response (Failure):** `404 Not Found`, `409 Conflict` (if saga is in a non-cancellable state), `500 Internal Server Error`, `503 Service Unavailable`

## Configuration

The orchestrator supports the following configuration through environment variables:

```
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/create_order_saga_db
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
USER_SERVICE_URL=http://user-service:3001
ORDER_SERVICE_URL=http://order-service:3002
PAYMENT_SERVICE_URL=http://payment-service:3003
TIMER_SERVICE_URL=http://timer-service:3005
```

## Libraries and Dependencies

The orchestrator uses the following key dependencies:

- **Flask**: Web framework for the REST API
- **SQLAlchemy**: ORM for database interactions
- **kafka-python**: Kafka client for producing and consuming messages 
- **psycopg2-binary**: PostgreSQL database adapter
- **requests**: HTTP client for service-to-service communication

## Local Development

1. Start the required infrastructure:
   ```
   docker-compose up -d postgres kafka
   ```

2. Initialize the database:
   ```
   docker exec -it campusg-create-order-saga-orchestrator-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   ```

3. Start the service:
   ```
   docker-compose up -d create-order-saga-orchestrator
   ```

## Testing

### Automated Tests

Run the provided test scripts for automated testing:

```bash
# Test the full saga flow
cd services/create-order-saga-orchestrator
python test_saga.py
```

### Manual Testing

1. Start the saga with a POST request:

```bash
curl -X POST http://localhost:3101/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_123",
    "order_details": {
      "foodItems": [
        {
          "name": "Burger",
          "price": 12.99,
          "quantity": 1
        }
      ],
      "deliveryLocation": "North Campus"
    }
  }'
```

2. Use the Kafka test producer to simulate service events:

```bash
# When running from host machine (outside Docker)
bash test_create_order_saga.sh

# When running inside the Docker container
bash docker_test_saga.sh
```

3. Check saga status:

```bash
curl http://localhost:3101/api/sagas/YOUR_SAGA_ID
```

### Kafka Message Debugging

To inspect Kafka messages:

```bash
# View messages on a topic
docker exec -it campusg-kafka-1 kafka-console-consumer --bootstrap-server localhost:9092 --topic order_commands --from-beginning

# List all topics
docker exec -it campusg-kafka-1 kafka-topics --bootstrap-server localhost:9092 --list
```

## Message Formats

### Command Messages

```json
{
  "type": "command_type",
  "correlation_id": "saga_id",
  "timestamp": "ISO timestamp",
  "payload": {
    // Command-specific data
  }
}
```

### Event Messages

```json
{
  "type": "event_type",
  "correlation_id": "saga_id",
  "timestamp": "ISO timestamp",
  "payload": {
    // Event-specific data
  }
}
```

## Error Handling

The orchestrator handles various failure scenarios:

1. **Transient Failures**: Network issues or temporary service unavailability are handled with retries in the messaging system.
2. **Service Failures**: If a service fails to process a command, it publishes a failure event that the orchestrator handles.
3. **Orchestrator Failures**: The orchestrator's state is persisted in the database, allowing it to resume processing after restart.
4. **Kafka Connection Issues**: The service implements graceful handling for Kafka connectivity problems.

## Monitoring

The orchestrator logs all steps and state changes. To view logs:

```
docker logs -f campusg-create-order-saga-orchestrator-1
```

## Future Improvements

See the [Changelog](../../Changelogs/CHANGELOG_31_March_Create_Order_Saga.md) for details on:

1. **Rollback Mechanisms**: Adding comprehensive compensation transactions for cancellations
2. **Enhanced Testing**: More robust integration tests
3. **Performance Optimizations**: Kafka and database optimizations
