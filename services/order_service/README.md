
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

### HTTP API Endpoints

The service exposes the following Flask-based HTTP endpoints (defined in `app/api/routes.py`):

*   **`GET /health`**:
    *   **Purpose:** Basic health check.
    *   **Response:** `{'status': 'healthy'}`

*   **`GET /orders`**:
    *   **Purpose:** Retrieves all orders (paginated). Useful for debugging.
    *   **Query Parameters:** `page` (int), `limit` (int), `status` (string, e.g., "ACCEPTED"), `runnerId` (string)
    *   **Response:** Paginated list of order objects.

*   **`GET /getOrderDetails`**:
    *   **Purpose:** Retrieves details for a specific order.
    *   **Query Parameter:** `orderId` (string, required)
    *   **Response:** Single order object or 404.

*   **`GET /orders/customer/<customer_id>`**:
    *   **Purpose:** Retrieves orders for a specific customer (paginated).
    *   **Path Parameter:** `customer_id` (string)
    *   **Query Parameters:** `page` (int), `limit` (int)
    *   **Response:** Paginated list of order objects.

*   **`POST /createOrder`**:
    *   **Purpose:** Creates an order directly via API (CRUD style). Publishes `ORDER_CREATED` Kafka event.
    *   **Request Body:** `{ "customer_id": "...", "order_details": { "foodItems": [...], "storeLocation": "...", "deliveryLocation": "...", "deliveryFee": "..." } }`
    *   **Response:** Success message with new `order_id`.

*   **`POST /updateOrderStatus`**:
    *   **Purpose:** Updates an order's status directly via API. Publishes `ORDER_UPDATED` Kafka event.
    *   **Request Body:** `{ "orderId": "...", "status": "ACCEPTED" }` (Status must match `OrderStatus` enum)
    *   **Response:** Success message and updated order object.

*   **`POST /verifyAndAcceptOrder`**:
    *   **Purpose:** Allows a runner to accept an order. Publishes `ORDER_ACCEPTED` Kafka event.
    *   **Request Body:** `{ "orderId": "...", "runner_id": "..." }`
    *   **Response:** Success message with `order_id`.

*   **`POST /cancelOrder`**:
    *   **Purpose:** Cancels an order directly via API (if status allows). Publishes `ORDER_CANCELLED` Kafka event.
    *   **Request Body:** `{ "orderId": "..." }`
    *   **Response:** Success message and updated order object.

*   **`POST /cancelAcceptance`**:
    *   **Purpose:** Allows a runner to cancel their acceptance of an order. Publishes `ORDER_ACCEPTANCE_CANCELLED` Kafka event.
    *   **Request Body:** `{ "orderId": "..." }`
    *   **Response:** Success message and updated order object.

*   **`POST /clearRunner`**:
    *   **Purpose:** Clears the assigned runner from an order (if status allows). Publishes `ORDER_RUNNER_CLEARED` Kafka event.
    *   **Request Body:** `{ "orderId": "..." }`
    *   **Response:** Success message and updated order object.

*   **`POST /completeOrder`**:
    *   **Purpose:** Marks an order as completed directly via API. Publishes `ORDER_COMPLETED` Kafka event.
    *   **Request Body:** `{ "orderId": "..." }`
    *   **Response:** Success message and updated order object.

*   **`POST /testCreateOrder`**:
    *   **Purpose:** Creates an order directly via API (likely for testing, does not publish Kafka event).
    *   **Request Body:** `{ "customer_id": "...", "order_details": { "foodItems": [...], "deliveryLocation": "..." } }`
    *   **Response:** Success message with new `order_id`.

### Database Models

The service defines SQLAlchemy models in `app/models/models.py`:

- `Order`: Main order model with order details and status
- `OrderStatus`: Enum defining possible order statuses
- `PaymentStatus`: Enum defining possible payment statuses

### Kafka Interactions

The service uses Kafka for asynchronous communication, primarily driven by commands from saga orchestrators and publishing events reflecting order state changes. (Defined in `app/services/kafka_service.py`)

*   **Consumer:**
    *   **Topic:** `order_commands` (Default name)
    *   **Group ID:** `order-service-group` (Default name)
    *   **Consumed Command Types:**
        *   `type: 'create_order'`
            *   **Expected Payload:** `{ "customer_id": "...", "order_details": {...}, "saga_id": "...", "correlation_id": "..." }`
            *   **Action:** Creates an order record in the database. Publishes `order.created` event.
        *   `type: 'update_order_status'`
            *   **Expected Payload:** `{ "order_id": "...", "status": "...", "correlation_id": "..." }`
            *   **Action:** Updates the order's status in the database. Publishes `order.status_updated` event on success or `order.status_update_failed` on failure.
        *   `type: 'cancel_order'`
            *   **Expected Payload:** `{ "order_id": "...", "reason": "...", "correlation_id": "..." }`
            *   **Action:** Updates the order's status to `CANCELLED`. Publishes `order.cancelled` event.

*   **Producer:**
    *   **Topic:** `order_events` (Default name)
    *   **Produced Event Types (from Kafka Command Handlers):**
        *   `type: 'order.created'` (Payload: `order_id`, `customer_id`, `status`, `saga_id`, `correlation_id`)
        *   `type: 'order.status_updated'` (Payload: `order_id`, `status`, `saga_id`, `correlation_id`)
        *   `type: 'order.status_update_failed'` (Payload: `order_id`, `error`, `correlation_id`)
        *   `type: 'order.cancelled'` (Payload: `order_id`, `reason`, `correlation_id`)
    *   **Produced Event Types (from HTTP API Routes):**
        *   `ORDER_CREATED`
        *   `ORDER_UPDATED`
        *   `ORDER_ACCEPTED`
        *   `ORDER_CANCELLED`
        *   `ORDER_ACCEPTANCE_CANCELLED`
        *   `ORDER_RUNNER_CLEARED`
        *   `ORDER_COMPLETED`
        *   *(Common Payload for API events:* `{ 'customerId': ..., 'runnerId': ..., 'orderId': ..., 'status': '...', 'event': json.dumps(order.to_dict()), 'correlation_id': '...', 'source': 'order-service' }`*)*

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
