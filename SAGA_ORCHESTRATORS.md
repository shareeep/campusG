# CampusG Saga Orchestrators

This document provides a detailed explanation of the three saga orchestrators used in the CampusG food delivery application. Each saga manages a specific part of the order lifecycle and coordinates multiple microservices.

## What is a Saga?

A saga is a sequence of local transactions where each transaction updates data within a single service. If a transaction fails, the saga executes compensating transactions to undo the changes made by preceding transactions.

In CampusG, we use the **Orchestration-based Saga** pattern where a central coordinator (the Order Service) directs and coordinates the participants.

## 1. Create Order Saga

The Create Order Saga manages the process of creating a new food delivery order.

### Flow Steps

1. **Initiate Order Creation**
   - Order Service creates a pending order
   - Publishes `ORDER_INITIATED` event

2. **Verify User and Payment Method**
   - Calls User Service to verify user exists and has valid payment method
   - If invalid, triggers compensation: Cancel order creation

3. **Authorize Payment**
   - Calls Payment Service to authorize payment
   - Publishes `PAYMENT_AUTHORIZED` event
   - If fails, triggers compensation: Cancel order

4. **Place Funds in Escrow**
   - Calls Escrow Service to hold funds
   - Publishes `FUNDS_HELD` event
   - If fails, triggers compensation: Revert payment authorization

5. **Start Order Timer**
   - Calls Timer Service to start 30-minute timer for runner acceptance
   - Publishes `TIMER_STARTED` event
   - If fails, triggers compensation: Release escrow and revert payment

6. **Complete Order Creation**
   - Updates order status to "Created"
   - Publishes `ORDER_CREATED` event

### Compensation Transactions

- **Cancel Order Creation**: Delete the pending order
- **Revert Payment Authorization**: Call Payment Service to revert authorization
- **Release Escrow**: Call Escrow Service to release funds back to customer
- **Cancel Timer**: Call Timer Service to cancel the timer

### Service Interactions

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ User Service│    │Payment Service│   │Escrow Service│   │Timer Service │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │                  │
       │                  │                  │                  │
┌──────┼──────────────────┼──────────────────┼──────────────────┼──────┐
│      │   Check User     │  Authorize       │   Hold Funds     │ Start Timer
│      │◄─────────────────┘      Payment     │◄─────────────────┘      │
│      │                  │◄─────────────────┘                  │      │
│ Order│                  │                  │                  │      │
│Service                  │                  │                  │      │
│      │                  │                  │                  │      │
│      │                  │                  │                  │      │
└──────┴──────────────────┴──────────────────┴──────────────────┴──────┘
```

## 2. Accept Order Saga

The Accept Order Saga manages the process of a runner accepting an order.

### Flow Steps

1. **Initiate Order Acceptance**
   - Order Service receives runner acceptance request
   - Verifies order is available
   - Publishes `ORDER_ACCEPTANCE_INITIATED` event

2. **Bind Runner to Order**
   - Order Service updates order with runner information
   - Publishes `RUNNER_ASSIGNED` event

3. **Stop Order Timer**
   - Calls Timer Service to stop the timer
   - Publishes `TIMER_STOPPED` event
   - If fails, triggers compensation: Unbind runner from order

4. **Send Notifications**
   - Calls Notification Service to notify customer
   - Publishes `ORDER_ACCEPTED` event

5. **Complete Order Acceptance**
   - Updates order status to "Accepted"
   - Publishes `ORDER_ACCEPTANCE_COMPLETED` event

### Compensation Transactions

- **Unbind Runner**: Remove runner from order and revert to "Created" status
- **Restart Timer**: Restart the acceptance timer if needed

### Service Interactions

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│Timer Service │    │Order Service │    │Notification │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │                  │                  │
       │                  │  Assign Runner   │
       │  Stop Timer      │                  │
       │◄─────────────────┘                  │
       │                  │                  │
       │                  │  Send            │
       │                  │  Notification    │
       │                  ├─────────────────►│
       │                  │                  │
```

## 3. Complete Order Saga

The Complete Order Saga manages the delivery process after a runner has accepted an order.

### Flow Steps

1. **Runner Arrives at Store (On-Site)**
   - Order Service updates order status to "On-Site"
   - Publishes `RUNNER_ON_SITE` event

2. **Runner Places Order (Purchased)**
   - Order Service updates order status to "Purchased"
   - Publishes `ORDER_PURCHASED` event

3. **Runner Collects Order (Collected)**
   - Order Service updates order status to "Collected"
   - Publishes `ORDER_COLLECTED` event

4. **Runner En Route (On-The-Way)**
   - Order Service updates order status to "On-The-Way"
   - Publishes `RUNNER_ON_THE_WAY` event

5. **Delivery Confirmation (Delivered)**
   - Order Service updates order status to "Delivered"
   - Publishes `ORDER_DELIVERED` event
   - If fails, triggers compensation: Revert to previous status

6. **Release Funds from Escrow**
   - Calls Escrow Service to release funds to runner
   - Publishes `FUNDS_RELEASED` event
   - If fails, logs error but does not revert delivery (manual resolution)

7. **Complete Order Process**
   - Updates order status to "Completed"
   - Updates customer and runner ratings
   - Publishes `ORDER_COMPLETED` event

### Service Interactions

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│Order Service │    │Escrow Service│   │Notification │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │  Status Updates  │                  │
       │  (On-Site,       │                  │
       │   Purchased,     │                  │
       │   Collected,     │                  │
       │   On-The-Way,    │                  │
       │   Delivered)     │                  │
       │                  │                  │
       │                  │                  │
       │  Release Funds   │                  │
       ├─────────────────►│                  │
       │                  │                  │
       │  Order Completed │                  │
       ├─────────────────────────────────────►
       │                  │                  │
```

## Saga Orchestration Implementation

All saga orchestrators are implemented in the Order Service under the `app/sagas` directory:

- `create_order_saga.py` - Manages order creation
- `accept_order_saga.py` - Manages runner acceptance
- `complete_order_saga.py` - Manages delivery process

Each saga orchestrator follows these implementation principles:

1. **Step Definitions**: Clear methods for each saga step
2. **Error Handling**: Comprehensive handling of failures
3. **Compensation Transactions**: Methods to undo each step if needed
4. **Event Publishing**: Kafka events published at each step
5. **Status Updates**: Database updates at each step

## Testing Sagas

Testing sagas requires both unit tests and integration tests:

### Unit Tests

- Test individual saga steps
- Mock external service calls
- Verify compensation logic

### Integration Tests

- Test end-to-end flows with actual service interactions
- Verify that saga completes successfully in happy path
- Verify compensation works in failure scenarios

## Error Handling

Saga orchestrators must handle various errors:

1. **Temporary Service Failures**: Retry with exponential backoff
2. **Permanent Service Failures**: Execute compensation transactions
3. **Partial Failures**: Handle cases where a compensation fails
4. **Timeout Handling**: Deal with long-running operations

## Best Practices

1. **Idempotency**: All operations should be idempotent (can be retried safely)
2. **Event Sourcing**: Record all saga actions as events
3. **Visibility**: Log all saga steps and state transitions
4. **Monitoring**: Track saga execution metrics
5. **Manual Intervention**: Provide admin tools for fixing stuck sagas
