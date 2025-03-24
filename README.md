# CampusG - Campus Food Delivery Application

CampusG is a microservices-based food delivery application designed for campus environments. It enables customers to place food orders and have them delivered by runners.

## System Architecture

The application follows a microservices architecture with the following components:

### Core Services

- **User Service**: Manages user accounts, authentication, and user data (TypeScript/Node.js)
- **Order Service**: Handles basic CRUD operations for orders (Python/Flask)
- **Payment Service**: Processes payments via Stripe integration (TypeScript/Node.js)
- **Escrow Service**: Manages fund holding and release (TypeScript/Node.js)
- **Scheduler Service**: Handles time-based events and order timeouts (TypeScript/Node.js)
- **Notification Service**: Sends notifications to users about order status changes (TypeScript/Node.js)
- **Timer Service**: Manages timing-related operations (TypeScript/Node.js)

### Saga Orchestrator Services

The application implements a decoupled saga orchestration pattern with dedicated microservices:

- **Create Order Saga Orchestrator**: Manages the entire order creation workflow, including payment authorization and escrow placement (Python/Flask)
- **Accept Order Saga Orchestrator**: Manages the runner assignment workflow (Python/Flask)
- **Complete Order Saga Orchestrator**: Manages the order delivery and payment release workflow (Python/Flask)

Each Saga Orchestrator is a standalone composite microservice that:
- Maintains its own state in a dedicated database
- Coordinates multiple service calls to complete a business transaction
- Handles compensation (rollback) logic when any step fails
- Exposes APIs for initiating or querying saga processes

### Communication Patterns

Services communicate through:
- Direct HTTP API calls for synchronous operations
- Kafka events for asynchronous notifications

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js (v16+) and npm (for TypeScript services and frontend)
- Python 3.11+ and pip (for Order Service)
- PostgreSQL (if running services locally)
- Kafka (if running services locally)

### Docker Compose Setup Instructions

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
   docker-compose up -d
   ```
   
   Or start specific services:
   ```
   docker-compose up -d frontend user-service payment-service
   ```

4. Verify containers are running and initialize the database for each service (required first time setup):
   ```
   # Check running containers
   docker ps
   ```

   If the services are running, initialize their databases:
   ```
   # For user-service
   docker exec -it campusg-user-service-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   ```

   If a container isn't running, start it first, then initialize:
   ```
   # Start a specific service if it's not running
   docker-compose up -d user-service
   
   #If you made a new enpoint and its not working e.g. in user-service
   docker-compose build user-service && docker-compose up -d user-service

   # Then initialize its database
   docker exec -it campusg-user-service-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   ```

   Repeat the same process for other services:
   ```
   # For order_service
   docker-compose up -d order-service
   docker exec -it campusg-order-service-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"

   # For payment-service
   docker-compose up -d payment-service
   docker exec -it campusg-payment-service-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   
   # For escrow-service
   docker-compose up -d escrow-service
   docker exec -it campusg-escrow-service-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   
   # For notification-service
   docker-compose up -d notification-service
   docker exec -it campusg-notification-service-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   
   # For timer-service
   docker-compose up -d timer-service
   docker exec -it campusg-timer-service-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   ```

5. Access the frontend at `http://localhost:3000`

### Common Issues and Fixes

1. **Flask Werkzeug Compatibility Issues**: 
   - If you see errors with `url_quote` or other Werkzeug-related errors, ensure that each service's requirements.txt includes:
   ```
   Werkzeug==2.2.3
   ```
   - The Dockerfiles for each service have been updated to explicitly install this version
   - To force rebuilding all services with the fixed Werkzeug version, use:
   ```
   docker-compose build --no-cache
   docker-compose up -d
   ```

2. **Database Tables Don't Exist Error**:
   - If you get "relation does not exist" errors, you need to initialize and run database migrations for that service
   - First check if the container is running, and start it if needed:
   ```
   # Check status
   docker ps
   
   # Start if needed
   docker-compose up -d <service-name>
   ```
   - Then run migrations inside the container:
   ```
   docker exec -it campusg-<service-name>-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   ```
   - For example, for the user-service:
   ```
   docker exec -it campusg-user-service-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   ```

3. **Datetime UTC Issues**:
   - If you encounter datetime errors related to `datetime.UTC`, ensure you're using the correct import:
   ```python
   from datetime import datetime, timezone
   # Use timezone.utc instead of datetime.UTC
   created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
   ```
   - All services' models files have been updated to use the correct timezone import

4. **Container Exiting Unexpectedly**:
   - If containers are starting but exiting right away, check the logs:
   ```
   docker logs campusg-<service-name>-1
   ```
   - Look for error messages that indicate dependency or code issues
   - Common issues include Flask compatibility errors or database connection problems

5. **Flask Migration Errors**:
   - If you see "Can't locate revision identified by 'XXXX'" when running migrations, the migrations directory might be in an inconsistent state
   - To fix this, you can remove the migrations directory in the container and reinitialize:
   ```
   # First, access the container
   docker exec -it campusg-<service-name>-1 bash
   
   # Inside the container, remove the migrations directory
   cd /app
   rm -rf migrations
   
   # Then exit the container
   exit
   
   # Now run the migration commands again
   docker exec -it campusg-<service-name>-1 bash -c "cd /app && flask db init && flask db migrate -m 'initial migration' && flask db upgrade"
   ```
   - Alternatively, you can rebuild and start the containers from scratch:
   ```
   docker-compose down -v  # -v removes volumes too, which means the database will be wiped
   docker-compose build --no-cache
   docker-compose up -d
   ```
   - Then run the migration commands for each service

## Deploying with Kubernetes

### Prerequisites

- Docker Desktop with Kubernetes enabled
- kubectl command-line tool (comes with Docker Desktop)

### Enabling Kubernetes in Docker Desktop

1. Open Docker Desktop
2. Go to Settings/Preferences
3. Select "Kubernetes" in the left sidebar
4. Check "Enable Kubernetes"
5. Click "Apply & Restart"
6. Wait for Kubernetes to start (may take a few minutes)

### Deploying CampusG to Kubernetes

1. Build the Docker images:
   ```
   cd kubernetes/setup
   ./build-images.sh
   ```

2. Deploy the application:
   ```
   kubectl apply -f kubernetes/infrastructure/namespace.yaml
   kubectl apply -f kubernetes/infrastructure/postgres/
   kubectl apply -f kubernetes/infrastructure/kafka/
   kubectl apply -f kubernetes/services/
   kubectl apply -f kubernetes/frontend/
   ```
   
   Or use the setup script:
   ```
   cd kubernetes/setup
   ./minikube-setup.sh
   ```

3. Add entry to hosts file for local development:
   - Windows: Edit `C:\Windows\System32\drivers\etc\hosts`
   - macOS/Linux: Edit `/etc/hosts`
   
   Add: `127.0.0.1 campusg.local`

4. Access the application at http://campusg.local

### Checking Deployment Status

```
# View all resources in the campusg namespace
kubectl get all -n campusg

# Check pod status
kubectl get pods -n campusg

# View logs for a specific pod
kubectl logs <pod-name> -n campusg -f
```

### Stopping the Kubernetes Deployment

```
kubectl delete namespace campusg
```

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
- **Orchestration**: Kubernetes
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
├── kubernetes/                # Kubernetes configuration files
│   ├── infrastructure/        # Infrastructure resources (Postgres, Kafka)
│   ├── services/              # Service deployments
│   ├── frontend/              # Frontend deployment
│   ├── setup/                 # Setup and deployment scripts
│   └── KUBERNETES.md          # Detailed Kubernetes documentation
└── scripts/                   # Setup and utility scripts
```

## Development Notes

- The order service uses Flask and is found in `services/order_service/` (note the underscore)
- Other services use TypeScript and follow a similar structure
- Service-specific documentation can be found in the README.md file within each service directory
- Frontend uses Next.js App Router and includes both customer and runner interfaces
