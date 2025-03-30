# Docker Startup Guide for CampusG

This guide walks you through running the CampusG microservices application using Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed
- Git repository cloned locally
- Basic understanding of Docker and microservices

## System Architecture

CampusG consists of several microservices:

- **User Service** - User management and authentication (port 3001)
- **Order Service** - Order processing and saga orchestration (port 3002)
- **Payment Service** - Payment processing via Stripe (port 3003)
- **Escrow Service** - Fund holding and release (port 3004)
- **Scheduler Service** - Scheduled tasks and timeouts (port 3005)
- **Notification Service** - User notifications (port 3006)
- **Timer Service** - Order timeout management (port 3007)
- **Frontend** - React-based user interface (port 3000)

Each service has its own PostgreSQL database and communicates with others through REST APIs and Kafka.

## Quick Start

1. **Start the entire application**:

```bash
docker-compose up -d
```

This command starts all services, databases, and Kafka in detached mode. It will build Docker images for each service if they don't exist.

2. **Access the application**:

Open your browser and navigate to `http://localhost:3000` to access the frontend.

## Step-by-Step Startup

If you prefer a more controlled startup, you can bring up services in groups:

1. **Start infrastructure components**:

```bash
# Start databases
docker-compose up -d user-db order-db payment-db escrow-db scheduler-db notification-db timer-db

# Start Kafka
docker-compose up -d zookeeper kafka
```

2. **Start backend services**:

```bash
# Start core services
docker-compose up -d user-service order-service 

# Start financial services
docker-compose up -d payment-service escrow-service

# Start support services
docker-compose up -d scheduler-service notification-service timer-service
```

3. **Start frontend**:

```bash
docker-compose up -d frontend
```

## Service URLs

Once all services are running, they can be accessed at:

- Frontend: `http://localhost:3000`
- User Service: `http://localhost:3001`
- Order Service: `http://localhost:3002`
- Payment Service: `http://localhost:3003`
- Escrow Service: `http://localhost:3004`
- Scheduler Service: `http://localhost:3005`
- Notification Service: `http://localhost:3006`
- Timer Service: `http://localhost:3007`

## Monitoring

### Viewing Logs

```bash
# View logs for a specific service
docker-compose logs -f order-service

# View logs for multiple services
docker-compose logs -f order-service payment-service

# View all logs
docker-compose logs -f
```

### Service Status

```bash
# Check status of all services
docker-compose ps
```

### Database Inspection

```bash
# Connect to a specific database (e.g., order-db)
docker-compose exec order-db psql -U postgres -d order_db
```

### Kafka Monitoring

See the `KAFKA_USAGE_GUIDE.md` for detailed Kafka monitoring and inspection commands.

## Common Issues and Troubleshooting

### Services Not Starting

If a service fails to start, check its logs:

```bash
docker-compose logs service-name
```

Common issues include:
- Database connection problems
- Kafka connection issues
- Missing environment variables

### Database Connection Issues

If services can't connect to databases, ensure the databases are running and healthy:

```bash
docker-compose ps | grep db
```

All databases should show as "healthy" in the status.

### Kafka Connection Issues

If services can't connect to Kafka, check Kafka's status:

```bash
docker-compose logs kafka
```

Make sure services are using the correct broker address (`kafka:29092` inside Docker network).

## Stopping the Application

```bash
# Stop all services but keep data volumes
docker-compose down

# Stop all services and remove data volumes (USE WITH CAUTION - DESTROYS ALL DATA)
docker-compose down -v
```

## Rebuilding Services

If you make code changes, rebuild the affected service:

```bash
docker-compose build service-name
docker-compose up -d service-name
```

Or rebuild and restart all services:

```bash
docker-compose build
docker-compose up -d
```

## Environment Variables

The docker-compose.yml file defines default environment variables. For production use, consider creating a `.env` file with sensitive information like:

```
STRIPE_API_KEY=your_stripe_key
STRIPE_WEBHOOK_SECRET=your_webhook_secret
SECRET_KEY=your_app_secret_key
```

## Next Steps

Now that your application is running, you can:

1. Complete the remaining TO-DO items from the TO-DO.md file
2. Implement the Kafka consumers for notification events
3. Add the timeout worker for the Scheduler Service
4. Create end-to-end tests for the complete saga workflow
