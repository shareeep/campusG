# Order Service (Flask Implementation)

This service manages the lifecycle of orders in the CampusG food delivery application. It implements the saga pattern for order creation, acceptance, and completion.

## Technology Stack

- **Framework**: Flask
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Messaging**: Kafka
- **Container**: Docker
- **Language**: Python 3.11

## Directory Structure

```
services/order_service/
├── app/                        # Main application code
│   ├── __init__.py            # Flask application factory
│   ├── api/                   # API endpoints
│   │   ├── __init__.py
│   │   └── routes.py          # API route definitions
│   ├── config/                # Configuration
│   │   ├── __init__.py
│   │   └── config.py          # Configuration settings
│   ├── models/                # Database models
│   │   ├── __init__.py
│   │   └── models.py          # SQLAlchemy models
│   ├── sagas/                 # Saga implementations
│   │   ├── __init__.py
│   │   └── create_order_saga.py # Create Order Saga
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   └── kafka_service.py   # Kafka integration
│   └── utils/                 # Utility functions
│       └── __init__.py
├── migrations/                # Database migrations (optional)
├── tests/                     # Test cases
├── Dockerfile                 # Container configuration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── run.py                     # Application entry point
```

## Key Components

### Saga Pattern Implementation

The service implements the orchestration-based saga pattern to coordinate distributed transactions:

1. **Create Order Saga** (`app/sagas/create_order_saga.py`)
   - Orchestrates the creation of a new order
   - Manages payment authorization
   - Sets up escrow for funds
   - Includes compensating transactions for error handling

### API Routes

The service exposes RESTful endpoints in `app/api/routes.py`:

- `GET /api/orders`: Get all orders with pagination
- `GET /api/orders/<order_id>`: Get a specific order
- `POST /api/orders`: Create a new order
- `PATCH /api/orders/<order_id>/status`: Update an order's status
- `POST /api/orders/<order_id>/accept`: Accept an order (runner)
- `POST /api/orders/<order_id>/cancel`: Cancel an order
- `POST /api/orders/<order_id>/complete`: Complete an order

### Database Models

The service defines SQLAlchemy models in `app/models/models.py`:

- `Order`: Main order model with order details and status
- `OrderStatus`: Enum defining possible order statuses
- `PaymentStatus`: Enum defining possible payment statuses

### Kafka Integration

The service integrates with Kafka for event sourcing in `app/services/kafka_service.py`:

- Publishes events when order status changes
- Subscribes to relevant events from other services

## Development

### Running Locally

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set environment variables or use defaults from `app/config/config.py`

3. Run the service:
   ```
   python run.py
   ```

### Running with Docker

The service is configured to run with Docker and Docker Compose:

```
docker-compose up order-service
```

### Database

The service automatically creates database tables on startup using SQLAlchemy's `create_all()`.
