# CampusG Microservices - TO-DO List

> **IMPORTANT NOTICE:** Kafka-related implementation is currently ON HOLD. Focus on core service functionality first. Kafka integration will be revisited once all services are fully operational.

This document provides a clear, step-by-step guide for completing the implementation in our food delivery application. Tasks are organized by microservice and include difficulty ratings (1=easy, 5=hard).

## What We've Already Built

✅ Core Create Order Saga orchestrator (partially implemented)
✅ Payment Service API endpoints
✅ Escrow Service API endpoints 
✅ Scheduler Service API endpoints
✅ Database models for tracking orders, payments, escrow transactions, and scheduled events
✅ User Service API endpoints
✅ Timer Service API endpoints
✅ Notification Service API endpoints
✅ Updated database models for all services
✅ Kafka integration for all services (CURRENTLY ON HOLD - Do not modify Kafka code at this time)
✅ Fixed asynchronous code issues in Order Service API and Saga implementation (see CHANGELOG_21_March.md)

## What Still Needs To Be Completed

## 1. Order Service Microservice - Core Configuration

### 1.1 Update Configuration (Difficulty: 1)

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

## 2. Saga Orchestrators Implementation

Our system uses three primary saga orchestrators to manage complex workflows. Only the Create Order Saga has been partially implemented.

### 2.1 Complete Create Order Saga (Difficulty: 3)

- **File to modify:** `services/order_service/app/sagas/create_order_saga.py`
- **What it does:** Manages the entire order creation process including payment, escrow, and timeout scheduling
- **Why it's needed:** To ensure the complete order creation flow works properly with compensation transactions
- **Key additions needed:**
  - Improve error handling with detailed rollback mechanisms
  - Add additional logging and event publishing
  - Ensure proper interaction with all services

### 2.2 Implement Accept Order Saga (Difficulty: 4)

- **File to create:** `services/order_service/app/sagas/accept_order_saga.py`
- **What it does:** Manages the process of a runner accepting an order
- **Why it's needed:** To coordinate runner assignment, notifications, and timer handling
- **Key functionality:**
  - Verify order availability and bind runner
  - Update order status to "Accepted"
  - Send notifications to customer
  - Stop request timer
  - Handle rollback if runner cancels acceptance
- **Example implementation:**
  ```python
  class AcceptOrderSaga:
      """
      Accept Order Saga
      
      This saga orchestrates the process of a runner accepting an order:
      1. Verify order is available
      2. Bind runner to order
      3. Update order status to "Accepted"
      4. Stop request timer
      5. Send notification to customer
      """
      
      def execute(self, order_id, runner_id):
          # Implementation here
  ```

### 2.3 Implement Complete Order Saga (Difficulty: 5)

- **File to create:** `services/order_service/app/sagas/complete_order_saga.py`
- **What it does:** Manages the entire delivery process from runner arrival at store to delivery completion
- **Why it's needed:** To coordinate the multi-step delivery process and ensure proper fund release
- **Key functionality:**
  - Handle status transitions: on-site → purchased → collected → on-the-way → delivered → completed
  - Verify delivery confirmation
  - Release funds from escrow
  - Update ratings
  - Generate receipts and completion notifications
- **Example implementation:**
  ```python
  class CompleteOrderSaga:
      """
      Complete Order Saga
      
      This saga orchestrates the delivery process:
      1. Runner arrives at store (on-site)
      2. Runner places order (purchased)
      3. Runner collects order (collected)
      4. Runner is on the way to delivery (on-the-way)
      5. Runner completes delivery (delivered)
      6. System releases payment (completed)
      """
      
      def execute(self, order_id, status_update):
          # Implementation here
  ```

## 3. Notification Service Microservice

### 3.1 Create Kafka Consumer (Difficulty: 3) - ⚠️ POSTPONED

> **ON HOLD:** This task is postponed until Kafka implementation is reactivated. For now, implement direct API calls for notifications.

- **File to create:** `services/notification-service/app/consumers/order_events_consumer.py`
- **What it does:** Listens for events published by the sagas and sends notifications
- **Why it's needed:** To notify users about order status changes
- **Events to handle:**
  - Pending payment
  - Payment authorized
  - Escrow placed
  - Order created
  - Order accepted
  - Delivery updates
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

### 3.1.1 Temporary Alternative: Direct Notification API (Difficulty: 2)

- **File to create:** `services/notification-service/app/api/notification_routes.py`
- **What it does:** Provides direct API endpoints for sending notifications
- **Why it's needed:** To support notifications without relying on Kafka
- **Key endpoints to implement:**
  - `POST /api/notifications/send` - Send a notification
  - `GET /api/notifications/user/{user_id}` - Get notifications for a user

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

### 5.1 Create Integration Tests for Create Order Saga (Difficulty: 4)

- **File to create:** `services/order_service/tests/sagas/test_create_order_saga.py`
- **What it does:** Tests that the Create Order Saga executes correctly
- **Why it's needed:** To verify the saga works end-to-end and handles errors properly
- **Key test cases to include:**
  - Success path: Order created successfully
  - Error paths: User not found, payment fails, etc.

### 5.2 Create Integration Tests for Accept Order Saga (Difficulty: 4)

- **File to create:** `services/order_service/tests/sagas/test_accept_order_saga.py`
- **What it does:** Tests that the Accept Order Saga executes correctly
- **Key test cases to include:**
  - Success path: Runner accepts order
  - Error path: Runner cancels acceptance

### 5.3 Create Integration Tests for Complete Order Saga (Difficulty: 4)

- **File to create:** `services/order_service/tests/sagas/test_complete_order_saga.py`
- **What it does:** Tests that the Complete Order Saga executes correctly
- **Key test cases to include:**
  - Success path: Full delivery flow
  - Error paths: Issues at different stages of delivery

### 5.4 End-to-End Testing (Difficulty: 5)

- **Files to create/modify:** Various test files
- **What to do:** Test the complete flow from order creation to delivery completion
- **Test scenarios:**
  - Customer creates order → payment succeeds → order created → runner accepts → delivery completed
  - Customer creates order → payment fails → order cancelled
  - Order created → no runner accepts → timeout → order cancelled
  - Order accepted → runner cancels → order returns to available
  - Various delivery stage issues and resolutions

## Recommended Order of Implementation

For the best results, implement these tasks in this order:

1. Start with Order Service configuration (1.1) - This is simple but necessary
2. Complete the Create Order Saga (2.1) - Focus on the core workflow first
3. Implement Accept Order Saga (2.2) - This builds on the Create Order Saga
4. Implement direct Notification Service endpoints (3.1.1) - Temporary alternative to Kafka
5. Implement Scheduler Service worker (4.1) - This handles timeouts
6. Implement Complete Order Saga (2.3) - This is the most complex saga
7. Create integration tests (5.1-5.4) - Verify everything works properly

> **Note:** All Kafka-related tasks are postponed. The code for Kafka integration should remain in place but not be modified or relied upon at this time.

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

### REST-Based Communication (Current Focus)
- [REST API Best Practices](https://restfulapi.net/)
- [Designing RESTful APIs](https://www.oreilly.com/library/view/restful-web-apis/9781449359713/)

### Kafka for Event-Driven Architecture (For Future Reference)
- [Confluent Kafka Python](https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
