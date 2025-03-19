# CHANGELOG - March 19, 2025

## Microservice Implementation

### Database Models
- **Updated:** User Service model with `user_stripe_card` field and decimal ratings
- **Created:** Payment Service model with proper payment status transitions  
- **Created:** Timer Service model for tracking order timeouts and runner acceptance
- **Redesigned:** Notification Service model for simplified event tracking
- **Created:** Escrow Service model for funds management with proper status transitions

### API Implementation
- **User Service:**
  - Implemented GET `/users/<user_id>` endpoint for retrieving user information with payment details
  - Added PUT `/users/<user_id>/payment` endpoint for updating payment information
  - Added POST endpoints for updating customer and runner ratings
  - Implemented GET `/users/<user_id>/payment-info` for other services to retrieve payment data

- **Payment Service:**
  - Implemented POST `/payments/authorize` with mock Stripe integration (real integration code is commented out)
  - Added POST `/payments/revert` endpoint for payment authorization rollbacks
  - Added POST `/payments/move-to-escrow` endpoint for escrow fund transfer
  - All endpoints publish events to Kafka for cross-service communication

- **Timer Service:**
  - Implemented POST `/start-request-timer` for initiating order request timers
  - Added POST `/stop-request-timer` endpoint for when runners accept orders
  - Added POST `/cancel-timer` endpoint for order cancellations
  - Implemented GET `/check-order-timeout` endpoint for finding timed-out orders

- **Notification Service:**
  - Implemented POST `/send-notification` for generic notifications
  - Added POST `/send-notification/order-accepted` endpoint for order acceptance notifications
  - Implemented POST `/revert-notification` endpoint for superseding previous notifications
  - Added Twilio SMS integration placeholder (commented out for future implementation)

- **Escrow Service:**
  - Implemented POST `/escrow/hold` endpoint for placing funds in escrow
  - Added POST `/escrow/release` endpoint for releasing funds to runners
  - Added POST `/escrow/refund` endpoint for refunding customers
  - All endpoints publish events to Kafka for cross-service communication

### Kafka Integration
- Added `kafka_service.py` to all microservices with standardized publishing interface
- Implemented event-based communication between services
- Added support for centralized logging through Kafka
- Standardized message format with timestamps and typed payloads

### Infrastructure
- Added request tracing middleware for distributed tracing across services
- Implemented system logging models and APIs for centralized log querying
- Added error handling with compensating transactions for saga pattern
- Added proper exception handling with detailed error messages

### Documentation
- Created detailed SAGA_ORCHESTRATORS.md file documenting all three saga patterns
- Created KAFKA_USAGE_GUIDE.md with simple explanations of Kafka usage
- Created DOCKER_STARTUP_GUIDE.md for running the application
- Updated TO-DO.md with detailed saga implementation tasks

## Detailed Changes

### User Service Updates
- Renamed `payment_details` field to `user_stripe_card` for Stripe integration
- Converted user and runner ratings from Float to Decimal for precision
- Added detailed API endpoints for user management and rating updates

### Payment Service Implementation
- Created a new `Payment` model with proper fields for Stripe integration
- Implemented mock and real Stripe integration with clear documentation
- Added status transitions for payment lifecycle (INITIATING → AUTHORIZED → INESCROW/FAILED)

### Timer Service Implementation 
- Created a new Timer model for tracking order acceptance timeouts
- Implemented timer starting, stopping, and cancellation endpoints
- Added timeout checking mechanism to identify expired order requests

### Notification Service Updates
- Simplified notification model to focus on event messaging
- Added support for Twilio SMS integration (code prepared but commented out)
- Added notification status tracking with CREATED/SENT states

### Escrow Service Implementation
- Created comprehensive escrow model with proper status tracking
- Implemented fund holding, release, and refund operations
- Added fund flow tracking with detailed logging

### Docker Configuration
- Verified Docker Compose configuration for all microservices
- Ensured proper environment variables are passed to containers
- Added health checks for database dependencies

## Saga Orchestrators Status

Our application is designed with three main saga orchestrators:

1. **Create Order Saga** - ✅ Partially implemented
   - Core flow and framework is in place
   - Needs improved error handling and better rollback mechanisms
   - Current implementation handles payment authorization, escrow, and timeout scheduling

2. **Accept Order Saga** - ⬜ Not yet implemented  
   - Will handle the process of runners accepting orders
   - Will coordinate runner assignment, timer stopping, and customer notifications
   - Implements rollbacks if runners cancel their acceptance

3. **Complete Order Saga** - ⬜ Not yet implemented
   - Will manage the entire delivery process
   - Will handle multiple status transitions (on-site, purchased, collected, etc.)
   - Will coordinate fund release from escrow upon successful delivery

## Next Steps
- Complete Order Service configuration with service URLs for saga orchestration
- Finish the Create Order Saga with improved error handling
- Implement Accept Order Saga for runner assignment workflow
- Implement Complete Order Saga for the delivery process
- Implement Kafka consumers for notification events
- Create a timeout worker for the Scheduler Service
- Develop integration tests for all three saga workflows
