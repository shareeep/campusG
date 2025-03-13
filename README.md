# CampusG - Campus Food Delivery Application

CampusG is a microservices-based food delivery application designed for campus environments. It enables customers to place food orders and have them delivered by runners.

## System Architecture

The application follows a microservices architecture with the following components:

- **User Service**: Manages user accounts, authentication, and user data (TypeScript/Node.js)
- **Order Service**: Handles order creation and lifecycle management (Python/Flask)
- **Payment Service**: Processes payments via Stripe integration (TypeScript/Node.js)
- **Escrow Service**: Manages fund holding and release (TypeScript/Node.js)
- **Scheduler Service**: Handles time-based events and order timeouts (TypeScript/Node.js)
- **Notification Service**: Sends notifications to users about order status changes (TypeScript/Node.js)

Communication between services is handled through both HTTP APIs and Kafka message broker.

## Key Workflows

The application implements three main saga patterns:

1. **Create Order Saga**: Order creation, payment authorization, and initial processing
2. **Accept Order Saga**: Runner assignment and order acceptance 
3. **Complete Order Saga**: Order delivery and payment completion

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js (v16+) and npm (for TypeScript services and frontend)
- Python 3.11+ and pip (for Order Service)
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

3. Start all services using Docker Compose (recommended):
   ```
   docker-compose up
   ```
   
   Or start specific services:
   ```
   docker-compose up frontend order-service payment-service
   ```

4. Access the frontend at `http://localhost:3000`

## Running Services Individually

### Running TypeScript Services Locally (user-service, payment-service, etc.)

1. Install dependencies:
   ```
   cd services/user-service
   npm install
   ```

2. Set up environment variables or use defaults from service config

3. Start the service:
   ```
   npm run dev
   ```

### Running Order Service Locally (Python/Flask)

1. Install dependencies:
   ```
   cd services/order_service
   pip install -r requirements.txt
   ```

2. Set environment variables or use defaults from `app/config/config.py`

3. Run the service:
   ```
   python run.py
   ```

### Running the Frontend Locally

1. Install dependencies:
   ```
   cd frontend
   npm install
   ```

2. Start the development server:
   ```
   npm run dev
   ```

3. Access the frontend at `http://localhost:3000`

## Tech Stack

### Backend
- **TypeScript Services**: Node.js, TypeScript, Express, PostgreSQL, Prisma ORM
- **Order Service**: Python 3.11, Flask, SQLAlchemy, PostgreSQL
- **Message Broker**: Kafka
- **Authentication**: Clerk
- **Payment Processing**: Stripe

### Frontend
- **Framework**: Next.js, React
- **Styling**: Tailwind CSS, shadcn components
- **Language**: TypeScript

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Database**: PostgreSQL

## Directory Structure

```
campusG/
├── services/                  # Microservices directory
│   ├── user-service/          # User management service (TypeScript)
│   ├── order_service/         # Order management service (Python/Flask)
│   ├── payment-service/       # Payment processing service (TypeScript)
│   ├── escrow-service/        # Escrow service (TypeScript)
│   ├── scheduler-service/     # Scheduler service (TypeScript)
│   └── notification-service/  # Notification service (TypeScript)
├── frontend/                  # Next.js frontend
├── kafka/                     # Kafka configuration
└── scripts/                   # Setup and utility scripts
```

## Development Notes

- The order service uses Flask and is found in `services/order_service/` (note the underscore)
- Other services use TypeScript and follow a similar structure
- Service-specific documentation can be found in the README.md file within each service directory
- Frontend uses Next.js App Router and includes both customer and runner interfaces
