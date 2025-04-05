# Comprehensive Test Plan for Create Order Saga Orchestrator

## 1. Overview

This document outlines a comprehensive test plan for the Create Order Saga Orchestrator, focusing on the complete flow from UI interaction through various microservices and back to the UI. The saga orchestrator follows a pattern where services communicate primarily via Kafka messages, with the exception of the Timer Service which will use HTTP.

### 1.1 Saga Flow Diagram

```
UI → Create Order Saga Orchestrator
Create Order Saga Orchestrator → Kafka → Order Service
Order Service → Kafka → Create Order Saga Orchestrator
Create Order Saga Orchestrator → Kafka → User Service
User Service → Kafka → Create Order Saga Orchestrator
Create Order Saga Orchestrator → Kafka → Payment Service
Payment Service → Stripe → Payment Service → Kafka → Create Order Saga Orchestrator
Create Order Saga Orchestrator → Kafka → Order Service (update order status)
Order Service → Kafka → Create Order Saga Orchestrator
Create Order Saga Orchestrator → HTTP → Timer Service
Timer Service → Kafka → Create Order Saga Orchestrator
Create Order Saga Orchestrator → UI (Inform user order status)
```

## 2. Test Objectives

1. Verify the complete end-to-end flow of the Create Order Saga
2. Ensure proper communication between all services
3. Validate error handling and rollback capabilities
4. Confirm the Notification Service is logging all Kafka messages
5. Test HTTP integration with Timer Service (OutSystems placeholder)
6. Validate order cancellation and payment refund functionality

## 3. Test Components

### 3.1 Create Order Saga Orchestrator

The orchestrator is responsible for:
- Initiating the saga process
- Coordinating commands and events between services
- Managing saga state
- Handling success and failure scenarios

### 3.2 Involved Services

- **Order Service**: Creates and manages orders
- **User Service**: Provides user payment information
- **Payment Service**: Handles payment authorization through Stripe
- **Timer Service**: Manages order timeout (via HTTP)
- **Notification Service**: Logs all Kafka messages for auditing/notification purposes

### 3.3 Communication Patterns

- **Kafka**: Primary communication method for all service interactions except Timer Service
- **HTTP**: Used for communication with Timer Service (placeholder for OutSystems)
- **Correlation IDs**: Used to track messages across the entire flow

## 4. Complete Test Flow

### 4.1 Initial Request Flow

1. **UI to Create Order Saga Orchestrator**:
   - HTTP POST request to `/api/orders` endpoint
   - Include customer_id and order_details in request body
   - Orchestrator creates saga state record with status STARTED
   - Orchestrator publishes create_order command to Kafka

2. **Verify Notification Service Logging**:
   - Confirm create_order command is logged in notification database

### 4.2 Order Service Flow

1. **Order Service Processing**:
   - Order Service consumes create_order command from Kafka
   - Creates order with status PENDING
   - Publishes order.created event to Kafka with generated order_id

2. **Orchestrator Processing**:
   - Orchestrator consumes order.created event
   - Updates saga state with order_id and moves to GET_USER_DATA step
   - Publishes get_payment_info command to Kafka

3. **Verify Notification Service Logging**:
   - Confirm order.created event is logged in notification database
   - Confirm get_payment_info command is logged in notification database

### 4.3 User Service Flow

1. **User Service Processing**:
   - User Service consumes get_payment_info command from Kafka
   - Retrieves user payment information
   - Publishes user.payment_info_retrieved event to Kafka

2. **Orchestrator Processing**:
   - Orchestrator consumes user.payment_info_retrieved event
   - Updates saga state to AUTHORIZE_PAYMENT step
   - Publishes authorize_payment command to Kafka

3. **Verify Notification Service Logging**:
   - Confirm user.payment_info_retrieved event is logged in notification database
   - Confirm authorize_payment command is logged in notification database

### 4.4 Payment Service Flow

1. **Payment Service Processing**:
   - Payment Service consumes authorize_payment command from Kafka
   - Authorizes payment through Stripe API
   - Publishes payment.authorized event to Kafka

2. **Orchestrator Processing**:
   - Orchestrator consumes payment.authorized event
   - Updates saga state to UPDATE_ORDER_STATUS step
   - Publishes update_order_status command to Kafka

3. **Verify Notification Service Logging**:
   - Confirm payment.authorized event is logged in notification database
   - Confirm update_order_status command is logged in notification database

### 4.5 Order Status Update Flow

1. **Order Service Processing**:
   - Order Service consumes update_order_status command from Kafka
   - Updates order status to CREATED
   - Publishes order.status_updated event to Kafka

2. **Orchestrator Processing**:
   - Orchestrator consumes order.status_updated event
   - Updates saga state to START_TIMER step
   - Makes HTTP request to Timer Service (instead of Kafka)

3. **Verify Notification Service Logging**:
   - Confirm order.status_updated event is logged in notification database

### 4.6 Timer Service Flow (HTTP)

1. **Timer Service Processing**:
   - Timer Service receives HTTP request
   - Starts a timer for the order (placeholder in test)
   - Publishes timer.started event to Kafka

2. **Orchestrator Processing**:
   - Orchestrator consumes timer.started event
   - Updates saga state to COMPLETED
   - Returns successful response to UI

3. **Verify Notification Service Logging**:
   - Confirm timer.started event is logged in notification database

### 4.7 Final Verification

1. **Saga State**:
   - Verify saga state is COMPLETED in the database
   - Ensure all steps were properly tracked

2. **Notification Service**:
   - Query notification database to confirm all events were logged
   - Verify sequence and content of notifications

## 5. Order Cancellation Test Flow

### 5.1 Cancellation Request

1. **Initiate a Create Order Saga** as outlined above
2. **Progress the saga to the point after payment authorization**
3. **Trigger cancellation request**:
   - Send cancel_order command to the appropriate service
   - This should initiate a cancellation/refund flow

### 5.2 Payment Cancellation/Refund

1. **Payment Service Processing**:
   - Payment Service should process cancellation request
   - Use StripeService.cancel_or_refund_payment method
   - Handle either cancellation or refund depending on payment state
   - Publish payment.cancelled or payment.refunded event to Kafka

2. **Orchestrator Processing**:
   - Orchestrator should consume cancellation event
   - Update saga state accordingly
   - Publish additional commands to complete cancellation flow

### 5.3 Cancellation Verification

1. **Saga State**:
   - Verify saga state reflects cancellation
   - Ensure appropriate status is set (e.g., COMPENSATED)

2. **Payment Status**:
   - Verify payment record status in database is updated to REVERTED

3. **Notification Service**:
   - Confirm all cancellation events are logged in notification database

## 6. Timer Service HTTP Implementation

### 6.1 HTTP Endpoint Design

The Timer Service will expose an HTTP endpoint to replace the Kafka integration:

```
POST /api/timers
{
  "order_id": "string",
  "customer_id": "string",
  "timeout_at": "ISO8601 timestamp",
  "correlation_id": "string"
}
```

Response:
```
{
  "success": true,
  "message": "Timer started successfully",
  "timer_id": "string"
}
```

### 6.2 Configuration

The Timer Service URL will be configurable to facilitate future replacement with OutSystems:

```python
TIMER_SERVICE_URL = os.getenv('TIMER_SERVICE_URL', 'http://timer-service:3000')
```

### 6.3 Implementation Notes

- For testing, the Timer Service will immediately publish a timer.started event via Kafka
- In the future, this Kafka publishing can be removed when moving to OutSystems
- The Create Order Saga Orchestrator will be modified to use HTTP requests instead of Kafka for timer commands

## 7. Notification Service Verification

### 7.1 Verification Approach

All Kafka messages should be logged in the Notification Service database. Test will:

1. Establish a baseline (clear or mark database before test)
2. Verify each expected message is logged after each step
3. Query for a complete record at the end

### 7.2 Verification Queries

```python
def verify_notification_logged(event_type, correlation_id):
    """Verify a specific message was logged in the notification database"""
    notification = Notifications.query.filter_by(
        event_type=event_type,
        correlation_id=correlation_id
    ).first()
    
    assert notification is not None, f"Notification not found for event {event_type}"
    return notification

def count_saga_notifications(correlation_id):
    """Count all notifications for a given saga"""
    return Notifications.query.filter_by(
        correlation_id=correlation_id
    ).count()
```

## 8. Prerequisites and Setup

### 8.1 Environment Requirements

- All services running (Order, User, Payment, Timer, Notification)
- Kafka and Zookeeper running
- Database migrations applied
- Test data prepared (user accounts, payment methods)

### 8.2 Test Dependencies

- Kafka client for publishing test events
- HTTP client for API requests
- Database client for verification queries
- Stripe test mode

## 9. Test Execution

### 9.1 Setup Phase

1. Start all required services
2. Create test data (user, payment methods)
3. Clear or mark notification database for baseline

### 9.2 Execution Phase

1. Execute the Create Order Saga flow as outlined in section 4
2. Verify each step progresses correctly
3. Validate notification logging after each step
4. Execute the Cancellation flow as outlined in section 5

### 9.3 Verification Phase

1. Check saga state in database
2. Verify notification database contains all expected events
3. Validate final status of all records

## 10. Expected Outcomes

### 10.1 Success Criteria

1. Saga completes successfully through all steps
2. All expected Kafka messages are sent and received
3. HTTP communication with Timer Service works correctly
4. Notification Service logs all Kafka messages
5. Cancellation flow properly reverts/refunds payments
6. All database records reflect correct final state

### 10.2 Error Handling Expectations

1. System should handle service failures gracefully
2. Appropriate error events should be published
3. Notification Service should log error events
4. Saga state should reflect failures appropriately

## 11. Implementation Plan

1. Create test script that implements this test plan
2. Add HTTP client capability to Create Order Saga Orchestrator
3. Add HTTP endpoint to Timer Service
4. Implement verification queries for Notification Service
5. Add order cancellation support if not already present

## 12. Maintenance and Future Enhancement

1. When migrating to OutSystems:
   - Update timer service URL configuration
   - Remove Kafka event publishing from HTTP endpoint
   - Update verification steps as needed

2. Consider adding more error scenarios:
   - Service unavailability
   - Timeout handling
   - Partial failures
