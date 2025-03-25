# Changelog: 25 March 2025 - Timer Service Implementation

## Overview
This update implements the Timer Service with Kafka integration, enabling time-based event handling for order processing workflows. The Timer Service is a key component in the saga orchestration pattern, responsible for tracking order timeouts and triggering compensation flows when orders are not accepted by runners within the specified timeframe.

## Added Features

### Timer Service Core Functionality
- Implemented the Timer model with proper schema including `expires_at` field
- Added support for automatic calculation of expiration times (default 30 minutes)
- Made `runner_id` nullable to support the order creation flow 
- Implemented scheduled background task using APScheduler to check for expired timers every minute

### API Endpoints
- `/api/start-request-timer`: Create a new timer for an order
- `/api/stop-request-timer`: Stop a timer when a runner accepts an order
- `/api/cancel-timer`: Cancel a timer (e.g., when order is cancelled by customer)
- `/api/check-order-timeout`: Manual endpoint to check for expired timers
- `/api/timers/<timer_id>`: Get timer by ID
- `/api/timers/order/<order_id>`: Get timer by order ID
- `/api/test-quick-timer`: Special endpoint for testing that creates a timer with 1-minute expiration

### Kafka Integration
- Added proper Kafka event publishing for all timer events
- Configured Kafka topics via environment variables for flexibility
- Implemented the following event types:
  - `TIMER_STARTED`: When a new timer is created
  - `TIMER_STOPPED`: When a runner accepts an order
  - `TIMER_CANCELLED`: When an order is explicitly cancelled
  - `ORDER_TIMEOUT`: When a timer expires without runner acceptance

### Testing Tools
- Created a Kafka test consumer script for monitoring timer events
- Added comprehensive testing documentation
- Provided docker-compose configuration with Kafka and Zookeeper

## Infrastructure Changes
- Updated Docker configuration to include necessary environment variables for Kafka
- Added APScheduler to requirements.txt for background task scheduling
- Updated `__init__.py` to include app context for scheduled tasks

## Bug Fixes
- Fixed schema mismatch issue that was preventing proper timer expiration
- Added proper error handling and logging for scheduled tasks

## Next Steps
- Integration with Create Order Saga Orchestrator to handle timeout events
- Implementation of timeout notification flow
- Add metrics and monitoring for timer service reliability
