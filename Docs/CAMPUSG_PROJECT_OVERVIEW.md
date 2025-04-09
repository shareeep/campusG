# CampusG Project Overview

## Project Description

CampusG is a microservices-based food delivery platform that connects customers with runners who deliver food orders. The platform handles the entire order lifecycle from creation to payment processing and delivery completion.

## Architecture Overview

The system follows an event-driven microservices architecture with saga orchestration pattern:

```
┌────────────┐     ┌─────────┐     ┌─────────────────────┐     ┌─────────┐     ┌────────────┐
│ Microservice├────►  Kafka  ├────►│  Saga Orchestrator  ├────►  Kafka  ├────►│Microservice│
└────────────┘     └─────────┘     └─────────────────────┘     └─────────┘     └────────────┘
                        ▲                                          ▲
                        │                                          │
                        │                                          │
                        │          ┌─────────────────┐             │
                        └──────────┤Notification Svc │◄────────────┘
                                   └─────────────────┘
                                  (polls Kafka messages)
```

## Core Components

### Microservices

1. **User Service**: 
   - Manages user accounts, authentication, and profiles
   - Stores customer and runner information
   - Handles login/registration flows
   - Endpoints: `/users`, `/auth`, `/profiles`

2. **Order Service**:
   - Manages order creation and lifecycle
   - Tracks order status changes
   - Handles assignment of runners to orders
   - Endpoints: `/orders`, `/orders/{id}`, `/orders/{id}/status`

3. **Payment Service**:
   - Processes payments via Stripe integration
   - Handles payment verification
   - Manages refunds for cancelled orders
   - Endpoints: `/payments`, `/payments/webhook`

4. **Notification Service**:
   - Acts as a passive listener for all system events
   - Records all inter-service communication
   - Provides historical event data for auditing and debugging
   - Endpoints: `/notifications`, `/order/{id}/notifications`

5. **Timer Service**:
   - Handles scheduling and time-based operations
   - Manages timeouts for various processes
   - Endpoints: `/timers`, `/schedules`

### Saga Orchestrators

1. **Create-Order Saga**:
   - Coordinates the order creation workflow
   - Handles user verification, payment processing, and order confirmation
   - Manages failures and compensation transactions

2. **Accept-Order Saga**:
   - Coordinates the order acceptance workflow
   - Handles runner assignment and notifications

3. **Complete-Order Saga**:
   - Coordinates the order completion workflow
   - Handles payment finalization and feedback collection

### Infrastructure Components

1. **Kafka**:
   - Central message bus for all service communication
   - Configured with multiple topics for different event types
   - Topics include: `order_events`, `payment_events`, `user_events`, etc.
   - Bootstrap server: `kafka:9092` (in Docker network)

2. **PostgreSQL**:
   - Each service has its own dedicated database
   - Maintains service data isolation
   - Ensures independent scaling and performance

## Communication Patterns

1. **Event-Driven Communication**:
   - Services publish domain events to Kafka when state changes
   - Format: `{type: "event.type", correlation_id: "uuid", payload: {}, timestamp: "iso-date", source: "service-name"}`

2. **Saga Orchestration Flow**:
   - Microservice publishes event to Kafka (e.g., `order.created`)
   - Saga orchestrator consumes the event
   - Saga orchestrator performs business logic and state management
   - Saga orchestrator publishes command to Kafka (e.g., `payment.process`)
   - Next microservice consumes the command and performs its operation
   - Process continues until the transaction completes or compensating actions are taken

3. **Notification Service Role**:
   - Passively polls Kafka to capture all messages
   - Doesn't participate in transaction flow
   - Records events for audit and monitoring purposes

## Deployment

1. **Docker Containerization**:
   - Each service runs in its own Docker container
   - Docker Compose for local development
   - Services communicate via Docker network

2. **Kubernetes Ready**:
   - Can be deployed to Kubernetes cluster
   - Configuration included for K8s deployment

## Project Structure

```
campusG/
├── services/
│   ├── user-service/
│   ├── order-service/
│   ├── payment-service/
│   ├── notification-service/
│   ├── timer-service/
│   ├── create-order-saga-orchestrator/
│   ├── accept-order-saga-orchestrator/
│   └── complete-order-saga-orchestrator/
├── kafka/
│   └── config/
├── frontend/
├── docs/
└── kubernetes/
```

## Example Event Flow

Here's an example of how a complete order creation flow works:

1. Customer creates order → Order Service publishes `order.created` event to Kafka
2. Create-Order Saga consumes `order.created` → Publishes `payment.process` command to Kafka
3. Payment Service consumes `payment.process` → Processes payment → Publishes `payment.completed` event to Kafka
4. Create-Order Saga consumes `payment.completed` → Publishes `order.confirm` command to Kafka
5. Order Service consumes `order.confirm` → Updates order status → Publishes `order.confirmed` event to Kafka
6. Notification Service polls Kafka → Records all events in its database
