# Saga Orchestrators Decoupling - March 24, 2025

This changelog documents the architectural changes made to decouple saga orchestrators from the Order Service into standalone microservices.

## Created New Files and Directories

### Create Order Saga Orchestrator
- Created service directory: `services/create-order-saga-orchestrator/`
- Basic service files:
  - `requirements.txt`: Flask, SQLAlchemy, and other dependencies
  - `Dockerfile`: Based on Python 3.11-slim
  - `run.py`: Flask application entry point
- Application structure:
  - `app/__init__.py`: Flask application factory and configuration
  - `app/models/saga_state.py`: Data model for saga state tracking
  - `app/services/service_clients.py`: API clients for interacting with other services
  - `app/api/routes.py`: REST endpoints for saga orchestration

### Accept Order Saga Orchestrator
- Created service directory: `services/accept-order-saga-orchestrator/`
- Basic service files:
  - `requirements.txt`: Flask, SQLAlchemy, and other dependencies
  - `Dockerfile`: Based on Python 3.11-slim

### Complete Order Saga Orchestrator
- Created service directory: `services/complete-order-saga-orchestrator/`
- Basic service files:
  - `requirements.txt`: Flask, SQLAlchemy, and other dependencies
  - `Dockerfile`: Based on Python 3.11-slim

## Modified Existing Files

### Docker Compose
- Updated `docker-compose.yml`:
  - Added database services for each saga orchestrator:
    - `create-order-saga-db`
    - `accept-order-saga-db`
    - `complete-order-saga-db`
  - Added service definitions for saga orchestrators with appropriate environment variables:
    - `create-order-saga-orchestrator`
    - `accept-order-saga-orchestrator`
    - `complete-order-saga-orchestrator`
  - Mapped external ports: 3101, 3102, 3103
  - Added new volume definitions for saga databases

### Order Service
- Modified `services/order_service/app/api/routes.py`:
  - Removed saga orchestration logic from endpoints
  - Refactored `/createOrder` to `/orders` with RESTful API approach
  - Added simpler CRUD-focused endpoints:
    - `POST /orders`: Basic order creation without saga
    - `PUT /orders/<order_id>/status`: Update order status
    - `POST /orders/<order_id>/accept`: Accept an order
  - Moved order calculation logic directly into the Order Service
  - Removed dependencies on saga classes

### Documentation
- Updated `README.md`:
  - Added new "Saga Orchestrator Services" section
  - Updated architecture description
  - Clarified the distinction between core services and saga orchestrators
  - Explained the decoupled saga architecture approach

## Architecture Changes

### Saga State Management
- Created dedicated database for each saga type
- Implemented state tracking within each saga orchestrator
- Added status tracking enums for monitoring saga progress

### Service Communication
- Implemented service clients for orchestrator-to-service communication
- Created consistent error handling patterns
- Added compensation (rollback) logic for failed transactions

### API Endpoints
- Created saga-specific API endpoints:
  - `POST /api/orders`: Create Order Saga entry point
  - `GET /api/sagas`: List all saga instances
  - `GET /api/sagas/<saga_id>`: View specific saga state

## Clean-up Operations

- Removed entire saga directory from Order Service:
  - Deleted `services/order_service/app/sagas/` and all contained files
  - Removed `create_order_saga.py` implementation

- Updated Order Service documentation:
  - Updated `services/order_service/README.md` to reflect new architecture
  - Removed saga references from directory structure documentation
  - Updated API endpoints description
  - Updated key components section to focus on CRUD operations

## Completion Steps

- Created necessary files for Accept Order Saga Orchestrator:
  - Added `run.py` entry point
  - Added `app/__init__.py` with Flask application factory
  - Created directory structure:
    - `app/api/`
    - `app/models/`
    - `app/services/`
  - Added package `__init__.py` files to all directories

- Created necessary files for Complete Order Saga Orchestrator:
  - Added `run.py` entry point
  - Added `app/__init__.py` with Flask application factory  
  - Created directory structure:
    - `app/api/`
    - `app/models/`
    - `app/services/`
  - Added package `__init__.py` files to all directories

- Completed Docker and Kubernetes setup:
  - All saga orchestrator services ready to be started with docker-compose
  - Set up correct environment variables and dependencies in docker-compose.yml
  - Removed unnecessary service URL environment variables from Order Service
  - Added explanatory comments in the docker-compose.yml
  - Updated Kubernetes ConfigMap for order-service to remove unneeded service URLs
  - Updated Kubernetes Deployment for order-service to match the new ConfigMap

## Next Steps
- Complete implementation of Accept Order Saga Orchestrator
- Complete implementation of Complete Order Saga Orchestrator
- Add database migrations for all saga orchestrator services
- Update client code to call saga orchestrator endpoints
- Update any test files that might have been dependent on the old saga implementation
