
# Order Service (Flask Implementation)

This service manages the lifecycle of orders in the CampusG food delivery application. It provides CRUD operations for orders and communicates with the saga orchestrator services.

## Technology Stack

- **Framework**: Flask
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Messaging**: Kafka
- **Container**: Docker
- **Language**: Python 3.11
- **API**: RESTful endpoints

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

### Order Management

This service provides basic CRUD operations for orders:

1. **Create**: Create new orders with customer information and order details
2. **Read**: Retrieve order information and status
3. **Update**: Update order status and details
4. **Delete**: Cancel orders when needed

The complex transaction management is handled by dedicated saga orchestrator services that call these CRUD endpoints.

### API Routes

The service exposes RESTful endpoints in `app/api/routes.py`:

- `GET /api/orders`: Get all orders with pagination
- `GET /api/getOrderDetails`: Get a specific order
- `POST /api/orders`: Create a new order
- `PUT /api/orders/<order_id>/status`: Update an order's status
- `POST /api/orders/<order_id>/accept`: Accept an order (runner)
- `POST /api/cancelOrder`: Cancel an order
- `POST /api/cancelAcceptance`: Cancel runner acceptance

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
