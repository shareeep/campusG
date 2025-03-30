# Missing Components for Place Order Saga

To complete the Place Order Saga implementation, the following components still need to be developed:

## 1. User Service API Endpoint

The saga calls the User Service to validate customer data, but we haven't implemented this endpoint.

**Required file:**
- `services/user-service/app/api/user_routes.py` with:
  ```python
  @api.route('/users/<user_id>', methods=['GET'])
  async def get_user(user_id):
      # Should return user data with payment details
      # Called by CreateOrderSaga.get_user_data()
  ```

## 2. Kafka Service Implementation

The saga uses `kafka_client.publish()` to send events, but we haven't implemented this client.

**Required file:**
- `services/order_service/app/services/kafka_service.py`
  - Should implement a `KafkaClient` class with a `publish(topic, message)` method
  - Used by the saga for notifications and event publishing

## 3. Order Model Definition

The saga relies on the Order model, which should include OrderStatus and PaymentStatus enums.

**Required file:**
- `services/order_service/app/models/models.py` with:
  - `Order` class with appropriate fields and methods
  - `OrderStatus` enum with values like PENDING, CREATED, ACCEPTED, etc.
  - `PaymentStatus` enum with values like PENDING, AUTHORIZED, etc.

## 4. Notification Service Kafka Consumer

The saga publishes events to Kafka, but we need a consumer to process these events.

**Required file:**
- `services/notification-service/app/consumers/order_events_consumer.py`
  - Should consume events from the notification-events topic
  - Send notifications based on event type

## 5. Scheduler Service Worker

The saga schedules timeout events, but we need a worker to process them.

**Required file:**
- `services/scheduler-service/app/workers/timeout_worker.py`
  - Should periodically check for due events
  - Execute actions based on event type (e.g., timeout orders)

## 6. Environment Configuration

Services need to know how to communicate with each other.

**Required files:**
- `services/order_service/app/config/config.py` with service URLs
- Configuration files for other services

## 7. Integration Tests

To ensure the saga works end-to-end.

**Required file:**
- `services/order_service/tests/sagas/test_create_order_saga.py`
  - Should test the complete saga flow
  - Mock external service responses

## Order of Implementation

To get the saga working with minimal effort, implement in this order:

1. Order model definition
2. Kafka service implementation 
3. User service endpoint
4. Environment configuration
5. Notification service consumer (can be basic initially)
6. Scheduler service worker (can be basic initially)
7. Integration tests
