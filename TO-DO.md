# CampusG Microservices - TO-DO List

This document provides a clear, step-by-step guide for completing the **Create Order Saga** implementation in our food delivery application. Tasks are organized by microservice and include difficulty ratings (1=easy, 5=hard).

## What We've Already Built

✅ Core Create Order Saga orchestrator
✅ Payment Service API endpoints
✅ Escrow Service API endpoints
✅ Scheduler Service API endpoints
✅ Database models for tracking orders, payments, escrow transactions, and scheduled events

## What Still Needs To Be Completed

## 1. User Service Microservice

### 1.1 Create User API Endpoint (Difficulty: 2)

- **File to create:** `services/user-service/app/api/user_routes.py`
- **What it does:** Creates an endpoint that returns user information, including payment methods
- **Why it's needed:** The Create Order Saga needs to check if a user exists and has valid payment methods
- **Example functionality:**
  ```python
  @api.route('/users/<user_id>', methods=['GET'])
  async def get_user(user_id):
      # This endpoint should:
      # 1. Check if user exists
      # 2. Return user data with payment details
  ```

## 2. Order Service Microservice

### 2.1 Update Configuration (Difficulty: 1)

- **File to modify:** `services/order_service/app/config/config.py`
- **What to add:** Service URLs for all the microservices
- **Why it's needed:** The saga needs to know where to find other services
- **Example addition:**
  ```python
  # Service URLs
  USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://user-service:3000')
  PAYMENT_SERVICE_URL = os.environ.get('PAYMENT_SERVICE_URL', 'http://payment-service:3000')
  ESCROW_SERVICE_URL = os.environ.get('ESCROW_SERVICE_URL', 'http://escrow-service:3000')
  SCHEDULER_SERVICE_URL = os.environ.get('SCHEDULER_SERVICE_URL', 'http://scheduler-service:3000')
  NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service:3000')
  ```

### 2.2 Create Integration Tests (Difficulty: 4)

- **File to create:** `services/order_service/tests/sagas/test_create_order_saga.py`
- **What it does:** Tests that the entire saga workflow executes correctly
- **Why it's needed:** To verify the saga works end-to-end and handles errors properly
- **Key test cases to include:**
  - Success path: Order created successfully
  - Error paths: User not found, payment fails, etc.

## 3. Notification Service Microservice

### 3.1 Create Kafka Consumer (Difficulty: 3)

- **File to create:** `services/notification-service/app/consumers/order_events_consumer.py`
- **What it does:** Listens for events published by the Create Order Saga and sends notifications
- **Why it's needed:** To notify users about order status changes
- **Events to handle:**
  - Pending payment
  - Payment authorized
  - Escrow placed
  - Order created
- **Example structure:**
  ```python
  def handle_event(topic, event):
      event_type = event.get('type')
      payload = event.get('payload')
      
      if event_type == 'PENDING_PAYMENT':
          # Send notification about pending payment
      elif event_type == 'PAYMENT_AUTHORIZED':
          # Send notification about payment authorized
      # ... etc.
  ```

## 4. Scheduler Service Microservice

### 4.1 Create Timeout Worker (Difficulty: 3)

- **File to create:** `services/scheduler-service/app/workers/timeout_worker.py`
- **What it does:** Periodically checks for events that are due and executes them
- **Why it's needed:** The Create Order Saga schedules a timeout event after 30 minutes if no runner accepts the order
- **Key functionality:**
  - Find events that are due
  - For ORDER_TIMEOUT events, call Order Service to cancel the order
  - Update event status to PROCESSED
- **Example structure:**
  ```python
  def process_due_events():
      # Find events that are due
      # For each event:
      #   If ORDER_TIMEOUT:
      #     Call Order Service to cancel the order
      #     Update event status
  ```

## 5. Testing and Integration

### 5.1 End-to-End Testing (Difficulty: 5)

- **Files to create/modify:** Various test files
- **What to do:** Test the complete flow from order creation to all possible outcomes
- **Test scenarios:**
  - Customer creates order → payment succeeds → order created
  - Customer creates order → payment fails → order cancelled
  - Order created → no runner accepts → timeout → order cancelled

## Recommended Order of Implementation

For the best results, implement these tasks in this order:

1. Start with Order Service configuration (2.1) - This is simple but necessary
2. Then implement User Service endpoint (1.1) - The saga needs this first
3. Implement Notification Service consumer (3.1) - Start with a simple version
4. Implement Scheduler Service worker (4.1) - This completes the workflow
5. Finally, create integration tests (2.2, 5.1) - Verify everything works

## Learning Resources

### Microservices Architecture
- [Microservices.io](https://microservices.io/) - Great patterns and explanations
- [Martin Fowler on Microservices](https://martinfowler.com/articles/microservices.html) - The classic article

### Saga Pattern
- [Microservices.io: Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Chris Richardson's book: Microservices Patterns](https://www.manning.com/books/microservices-patterns)

### Python/Flask API Development
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask RESTful](https://flask-restful.readthedocs.io/en/latest/)

### Kafka for Event-Driven Architecture
- [Confluent Kafka Python](https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
