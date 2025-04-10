# CampusG - Food Delivery Platform

## 1. Overview

CampusG is a microservices-based application simulating a campus food delivery service. It connects customers placing orders with runners who deliver them. The system utilizes saga patterns (both Kafka-based and Temporal-based) to manage complex distributed transactions like order creation, acceptance, and completion/payment.

## 2. Architecture & Flow

The system follows a microservices architecture pattern. Key components and interactions include:

*   **Frontend (React/Vite):** The user interface for customers and runners. Interacts directly with various backend services via HTTP API calls.
*   **User Service (Flask):** Handles user authentication (via Clerk), profile management, and stores Stripe customer/connect account details.
*   **Order Service (Flask):** Manages the lifecycle of orders (creation, status updates, assignment).
*   **Payment Service (Flask):** Integrates with Stripe for handling payment intents, refunds, and payouts to runners.
*   **Notification Service (Flask):** Primarily acts as a Kafka consumer, logging events for observability and monitoring with Grafana.
*   **Create Order Saga (Flask/Kafka):** Orchestrates the complex process of creating a new order.
    *   Triggered by the Frontend.
    *   Uses Kafka commands/events to coordinate actions between Order Service (create order), User Service (get payment info), Payment Service (authorize payment), and Order Service again (update status).
    *   Communicates with the external Timer Service (Outsystems) via HTTP to start an order timer.
    *   Manages its state in a database and handles failures/compensation via Kafka events.
*   **Accept Order Saga (Temporal):** Orchestrates a runner accepting an order.
    *   Triggered by the Frontend (likely via an API gateway or directly).
    *   Uses Temporal activities to make HTTP calls to:
        *   Order Service: Verify and assign the runner to the order.
        *   Timer Service (Outsystems): Notify that the order is accepted (e.g., stop/update a timer).
    *   Handles compensation (e.g., reverting order status) if activities fail.
*   **Complete Order Saga (Temporal):** Orchestrates the final steps after delivery.
    *   Triggered by the Frontend (runner marks order as delivered).
    *   Uses Temporal activities to make HTTP calls to:
        *   Order Service: Update status to 'Delivered', then 'Completed'.
        *   User Service: Get the runner's Stripe Connect ID.
        *   Payment Service: Get the payment ID for the order.
        *   Payment Service: Release funds (payout) to the runner's Stripe account.
    *   Handles compensation (e.g., reverting payment release/order status) if activities fail.
*   **Kafka:** Acts as the central message bus for the Create Order Saga and event logging by the Notification Service.
*   **Temporal:** Provides reliable execution and state management for the Accept Order and Complete Order sagas.
*   **External Services:**
    *   **Clerk:** Handles user authentication.
    *   **Stripe:** Processes payments and payouts.
    *   **Timer Service (Outsystems):** Manages timers related to order acceptance/delivery deadlines. Start, Stop and Cancel Timers.
*   **Databases (PostgreSQL):** Used by individual services for data persistence.

## 3. Services Deep Dive

*   **`frontend`**: React, Vite, TypeScript, TailwindCSS. Handles UI for customers and runners.
*   **`services/user-service`**: Manages user profiles, Clerk authentication integration, Stripe customer and Connect account details.
*   **`services/order_service`**: Manages order creation, status updates (Pending, Created, Accepted, Delivered, Completed, Cancelled), and assignment to runners.
*   **`services/payment-service`**: Integrates with Stripe for payment intents, refunds, and payouts to runner Connect accounts.
*   **`services/notification-service`**: Logs Kafka events for system observability. Has Grafana for monitoring as well.
*   **`services/create-order-saga-orchestrator`**: Flask app orchestrating the multi-step order creation process via Kafka commands and events. Manages saga state in its own DB table. Interacts with Timer Service via HTTP.
*   **`services/accept-order-saga-orchestrator`**: Temporal worker/workflow coordinating runner acceptance, updating Order Service and notifying Timer Service via HTTP activities.
*   **`services/complete-order-saga-orchestrator`**: Temporal worker/workflow coordinating order completion, updating Order Service, fetching User/Payment info, and triggering payouts via HTTP activities.
*   **`kafka`**: Contains Kafka topic configuration.
*   **`temporal`**: Contains Temporal configuration.

## 4. Key Workflows (Sagas)

*   **Create Order:** Customer places order -> Saga coordinates Order creation -> User payment info retrieval -> Payment authorization (Stripe) -> Order status update -> Timer start (Outsystems). Handles failures with compensation (e.g., cancelling order if payment fails).
*   **Accept Order:** Runner accepts order -> Saga coordinates Order status update (assign runner) -> Timer notification (Outsystems). Handles failures with compensation (e.g., reverting order status).
*   **Complete Order:** Runner marks order delivered -> Saga coordinates Order status update -> Runner payment info retrieval -> Payment ID retrieval -> Fund release (Stripe payout) -> Final Order status update. Handles failures with compensation (e.g., reverting payout/status).

## 5. Getting Started

### Prerequisites

*   Docker & Docker Compose
*   Git
*   Access to external service credentials (Stripe, Clerk, Outsystems Timer API if needed)

### Environment Setup

1.  Clone the repository.
2.  Reference the `.env.example` to create it's matching `.env`.
3.  There is an additional `.env.local.example` within the root/frontend/.env.local
4.  Fill in the required environment variables in both env files.


### Building & Running

```bash
docker-compose up --build -d
```

*   This command builds the images (if necessary) and starts all services defined in `docker-compose.yml` in detached mode.
*   Wait for all services, Kafka, Temporal, and databases to initialize. Check logs using `docker-compose logs -f [service_name]`.

### Accessing Services

*   **Frontend:** `http://localhost:5173` 
*   **Temporal UI:** `http://localhost:8080`
*   **Grafana (Observability):** `http://localhost:3000` 

## 8. Project Structure

```
├── api-specs/        # OpenAPI specifications for services
├── Changelogs/       # Manual changelog files
├── Docs/             # Project documentation and guides
├── frontend/         # React/Vite frontend application
├── grafana/          # Grafana provisioning configuration
├── kafka/            # Kafka configuration (e.g., topics)
├── services/         # Backend microservices and saga orchestrators
│   ├── accept-order-saga-orchestrator/
│   ├── complete-order-saga-orchestrator/
│   ├── create-order-saga-orchestrator/
│   ├── notification-service/
│   ├── order_service/
│   ├── payment-service/
│   └── user-service/
├── temporal/         # Temporal server configuration
├── .env.example      # Example environment variables
├── .gitignore
├── docker-compose.yml # Main Docker Compose file for local development
└── README.md         # This file
```

## 9. API Documentation
Swagger is integrated into all services, as well as in the api-specs folder.
