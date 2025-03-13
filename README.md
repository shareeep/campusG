# CampusG - Campus Food Delivery Application

CampusG is a microservices-based food delivery application designed for campus environments. It enables customers to place food orders and have them delivered by runners.

## System Architecture

The application follows a microservices architecture with the following components:

- **User Service**: Manages user accounts, authentication, and user data
- **Order Service**: Handles order creation and lifecycle management
- **Payment Service**: Processes payments via Stripe integration
- **Escrow Service**: Manages fund holding and release
- **Scheduler Service**: Handles time-based events and order timeouts
- **Notification Service**: Sends notifications to users about order status changes

Communication between services is handled through both HTTP APIs and Kafka message queue.

## Key Workflows

The application implements three main saga patterns:

1. **Create Order Saga**: Order creation, payment authorization, and initial processing
2. **Accept Order Saga**: Runner assignment and order acceptance 
3. **Complete Order Saga**: Order delivery and payment completion

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js (v16+) and npm
- PostgreSQL (if running services locally)
- Kafka (if running services locally)

### Setup Instructions

1. Clone the repository:
   ```
   git clone https://github.com/your-username/campusG.git
   cd campusG
   ```

2. Set up environment variables:
   ```
   cp .env.example .env
   ```
   Edit the `.env` file to include your Stripe API keys and other configuration.

3. Start the services using Docker Compose:
   ```
   docker-compose up
   ```

4. Access the frontend at `http://localhost:3000`

## Development

Each microservice can be developed and run independently. See the README in each service directory for specific instructions.

## Tech Stack

- **Backend**: Node.js, TypeScript, Express, PostgreSQL, Prisma ORM
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, shadcn components
- **Authentication**: Clerk
- **Payment Processing**: Stripe
- **Message Broker**: Kafka
- **Containerization**: Docker

## Directory Structure

```
campusG/
├── services/                  # Microservices directory
│   ├── user-service/          # User management service
│   ├── order-service/         # Order management service
│   ├── payment-service/       # Payment processing service
│   ├── escrow-service/        # Escrow service
│   ├── scheduler-service/     # Scheduler service
│   └── notification-service/  # Notification service
├── frontend/                  # Next.js frontend
├── kafka/                     # Kafka configuration
└── scripts/                   # Setup and utility scripts
