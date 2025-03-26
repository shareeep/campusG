# CHANGELOG - March 18, 2025

## Database Architecture Overhaul

### Changed
- Replaced single PostgreSQL container with six independent database containers
- Each microservice now has its own dedicated database instance
- Updated all database connection strings in service configurations
- Configured separate data volumes for each database
- Assigned unique port mappings for each database service (5432-5437)

## Database Models Implementation

### Added
- User Service Model: Created complete `User` model with proper fields and relations
- Notification Service Model: Created complete `Notification` model with recipient types and status tracking

### Updated
- Order Service Model: Updated to match specified schema with order_id, cust_id, runner_id, etc.
- Payment Service Model: Updated to use payment_id and correct status enum values
- Escrow Service Model: Updated with escrow_id and required transaction tracking fields
- Scheduler Service Model: Updated with event types and processing status tracking

## Infrastructure Configuration

### Updated
- Docker Compose Configuration: Restructured for proper microservice isolation
- Service Dependencies: Corrected dependency chains to ensure proper startup order
- Health Checks: Added database health checks to prevent premature service startup
- Network Configuration: Configured proper hostname resolution for service discovery

## Application Setup

### Added
- User Service Initialization: Added proper database connection handling in app/__init__.py
- API Endpoint Structure: Implemented required endpoints for User Service

### Updated
- Order Service API: Renamed endpoints to match desired naming convention and implemented Kafka event publishing
  - `/createOrder`: For order creation
  - `/updateOrderStatus`: For status updates
  - `/cancelOrder`: For cancelling orders
  - `/verifyAndAcceptOrder`: For runner acceptance
  - `/cancelAcceptance`: For reverting runner acceptance (new endpoint)
  - `/completeOrder`: For finalizing orders
  - `/getOrderDetails`: For retrieving order information

## Detailed Changes

### Database Schema Updates
- Implemented proper enum types for all statuses
- Added appropriate indexes for frequently queried fields
- Set up proper data types for decimal values (using Numeric with precision/scale)
- Added UUID primary keys with automatic generation
- Configured timestamp fields with auto-update capabilities

### Data Model Improvements
- Added to_dict() methods for consistent JSON serialization
- Implemented proper repr() methods for debugging
- Added docstrings for better code documentation
- Setup appropriate nullable/non-nullable constraints

## Next Steps
- Complete API implementations for remaining services
- Implement Kafka consumers for event handling
- Finish saga pattern implementation
- Set up database migrations
- Complete integration testing
