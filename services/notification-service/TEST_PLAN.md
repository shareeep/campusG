# Notification Service Test Plan

This document outlines the test plan for verifying that the notification service correctly captures messages exchanged between microservices via Kafka.

## Testing Approach

The testing will involve both isolated testing of the notification service and integration testing with other microservices. The goal is to verify that:

1. The notification service correctly captures all messages sent to Kafka by other services
2. Messages with various formats and structures are properly parsed and stored
3. The notification service handles error conditions gracefully
4. API endpoints correctly return the stored notifications

## Prerequisites

- Kafka and Zookeeper running
- All microservices including notification service deployed
- Database for the notification service initialized

## Test Cases

### 1. Basic Connectivity Tests

**Objective**: Verify that the notification service connects to Kafka and starts consuming messages.

#### Test Steps:
1. Start Kafka and Zookeeper
2. Start the notification service
3. Check logs to verify that the consumer connects successfully
4. Check logs to verify that the consumer subscribes to all expected topics

**Expected Results**:
- Log entries showing successful connection to Kafka
- Log entries showing successful subscription to all topics
- No connection errors in the logs

### 2. Capture Messages from Other Services Test

**Objective**: Verify that messages sent by other services are captured by the notification service.

#### Test Steps:
1. Use the test_kafka_consumer.py script to send test messages to different topics
2. Use curl or Postman to verify that the messages were captured via the notification service API
3. Log into the database and verify records were created with the correct structure

**Expected Results**:
- New records appear in the notifications table for each test message
- Each record contains the correct metadata (source_topic, event_type, correlation_id, source_service)
- API endpoints return the newly created notifications in the expected format

### 3. End-to-End Order Flow Test

**Objective**: Verify that the notification service captures all messages in a complete order flow.

#### Test Steps:
1. Create a new order via the order service API
2. Track the order through its lifecycle (creation, acceptance, completion)
3. Use the notification service API to retrieve all notifications for the order

**Expected Results**:
- All events in the order lifecycle are captured as notifications
- The notifications are in chronological order
- Each notification contains the correct event type and metadata
- The latest notification shows the current status of the order

### 4. Cross-Service Communication Test

**Objective**: Verify that messages exchanged between different services are captured.

#### Test Steps:
1. Identify a flow that involves multiple services (e.g., order creation → payment → escrow)
2. Trigger this flow by creating a new order
3. Use the notification service API to verify all cross-service messages were captured

**Expected Results**:
- Messages from all services in the flow are captured
- The correlation_id is consistent across related messages 
- The sequence of events shows the correct flow of the transaction

### 5. Error Handling Tests

**Objective**: Verify that the notification service handles error conditions properly.

#### Test 5.1: Malformed Message Test
1. Send a malformed message to a Kafka topic (missing required fields, invalid JSON)
2. Verify that the notification service logs the error but continues processing other messages
3. Check that service remains operational

**Expected Results**:
- Error is logged but doesn't crash the service
- Service continues to process valid messages

#### Test 5.2: Kafka Connection Loss Test
1. Start the notification service with Kafka running
2. Stop Kafka while the service is running
3. Send test messages to a temporary topic
4. Restart Kafka
5. Verify the service reconnects and continues consuming

**Expected Results**:
- Service logs connection errors when Kafka is down
- Service automatically reconnects when Kafka becomes available again
- Service resumes consuming messages

### 6. High Volume Message Test

**Objective**: Verify that the notification service handles high message volumes.

#### Test Steps:
1. Create a script to send a large number of messages (e.g., 1000) to various topics
2. Run the script to flood Kafka with messages
3. Monitor the notification service logs and database
4. Verify all messages are captured

**Expected Results**:
- All messages are successfully captured and stored
- No performance degradation or crashes
- Database transactions complete successfully

### 7. API Endpoint Tests

**Objective**: Verify that the notification service API endpoints work correctly with the stored data.

#### Test 7.1: Get Latest Status Test
1. Create several notifications for the same order with different timestamps
2. Call the `/order/{order_id}/latest` endpoint
3. Verify that only the most recent notification is returned

**Expected Results**:
- Only the most recent notification is returned
- The notification contains the expected data

#### Test 7.2: Get All Updates Test
1. Create several notifications for the same order
2. Call the `/order/{order_id}` endpoint
3. Verify that all notifications for the order are returned in chronological order

**Expected Results**:
- All notifications for the order are returned
- The notifications are in chronological order (oldest first)
- Each notification contains the expected data

## Test Scripts

The testing will utilize the following scripts:

1. `test_kafka_consumer.py` - For sending test messages to Kafka topics
2. Additional curl/HTTP request scripts for API testing
3. SQL queries for database verification

## Documentation

For each test, document:
- Test date and time
- Test environment details (service versions, Kafka version)
- All test inputs
- Actual results vs. expected results
- Any errors or unexpected behavior
- Screenshots or logs for reference

## Acceptance Criteria

The notification service will be considered properly integrated when:

1. It successfully captures 100% of messages sent to Kafka
2. All metadata fields are correctly extracted and stored
3. No messages are lost due to errors or connection issues
4. API endpoints correctly return the stored notifications
5. The service operates reliably under normal and high-volume conditions
