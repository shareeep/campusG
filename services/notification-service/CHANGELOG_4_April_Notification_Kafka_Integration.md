# Notification Service Kafka Integration Changelog (4 April 2025)

## Overview

Implemented Kafka integration for the notification service to capture and store all events from Kafka in a central location. The notification service now functions as a passive listener that records all messages flowing through the Kafka message bus.

## Changes Made

### 1. Enhanced Database Schema

- Updated the `Notifications` model in `app/models/models.py`:
  - Made ID fields nullable to handle system events (customer_id, order_id)
  - Increased field lengths to accommodate various ID formats (from 36 to 255 chars)
  - Added new fields to store Kafka metadata:
    - `source_topic`: The Kafka topic the message came from
    - `event_type`: The type of event (from message payload)
    - `correlation_id`: For tracking the flow of events
    - `source_service`: The service that published the message

### 2. Replaced No-Op Kafka Client

- Replaced the dummy `kafka_service.py` with a functional consumer-only implementation
- Implemented singleton pattern for the Kafka client to ensure a single connection
- Added comprehensive error handling and logging
- Focused on consuming messages rather than publishing (per requirements)

### 3. Updated Kafka Consumer Logic

- Enhanced `consume_kafka_events()` function to:
  - Listen to all relevant topics across the system
  - Handle different message formats from various services
  - Extract important metadata like event type, correlation IDs
  - Support different field naming conventions (e.g., customerId vs customer_id)
  - Store complete message content for auditing purposes

### 4. Fixed Application Context Issues

- Modified the `start_kafka_consumer()` function to:
  - Create a thread with proper Flask application context
  - Ensure database operations can run within the app context
  - Add comprehensive exception handling
  - Provide additional logging for troubleshooting

### 5. Added Test Scripts

- Created `test_kafka_consumer.py` to:
  - Send test messages to Kafka topics
  - Verify the Kafka connection is working
  - Generate sample events for testing the capture logic

- Created `test_api.py` to:
  - Test the notification service REST API
  - Send and retrieve notifications
  - Verify the basic functionality of the service

### 6. Added Documentation and Test Plan

- Created `README.md` with detailed implementation information
- Created `TEST_PLAN.md` with comprehensive testing procedures:
  - Basic connectivity tests
  - Message capture tests
  - API functionality tests
  - End-to-end integration tests
  - Error handling tests

## Implementation Notes

- The notification service is intentionally designed as a consumer-only service
- It captures messages but does not publish to Kafka
- The service normalizes different message formats into a consistent database schema
- All event data is preserved in JSON format for complete auditing
- The API endpoints allow querying notifications by order ID

## Technical Decisions

1. **Consumer-Only Design**: Following the requirement that the notification service "is just like logging everything down from kafka," the implementation focuses exclusively on consuming and storing messages, not producing them.

2. **Flexible Schema**: The database schema was designed to accommodate a wide variety of message formats from different services, preserving all original data.

3. **Application Context**: Ensuring database operations run within the Flask application context was critical for proper functioning.

4. **Error Resilience**: The implementation includes comprehensive error handling to ensure the service continues functioning even if individual messages fail to process.

## Outstanding Issues and Next Steps

The following issues still need to be addressed to complete the implementation:

1. **Kafka Consumer Thread Not Processing Messages**:
   - While Kafka connection is established, messages sent to topics are not being captured
   - Logs show no errors, suggesting the consumer might be running but not receiving or processing messages

2. **Potential Root Causes to Investigate**:
   - Verify thread initialization in `start_kafka_consumer()` is working correctly
   - Check if main application is waiting for consumer threads to complete
   - Inspect if thread closure is happening prematurely
   - Verify that consumer groups are being properly registered with Kafka

3. **Debugging Approach**:
   - Add more verbose logging in `consume_kafka_events()` to confirm message reception
   - Implement a sync (non-threaded) version for testing
   - Add more logging to Flask application startup to verify thread activation
   - Consider implementing a simple standalone Kafka consumer script that doesn't use Flask context

4. **Implementation Steps**:
   - Add more debug logging to the consumer thread
   - Implement a non-daemon thread option (daemon threads might terminate prematurely)
   - Test with a simplified consumer outside the Flask application
   - Verify Kafka topic connection directly from container shell
