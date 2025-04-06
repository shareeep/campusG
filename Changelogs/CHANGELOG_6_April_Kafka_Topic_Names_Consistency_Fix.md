# Kafka Topic Names Consistency Fix - April 6, 2025

## Issue
The saga orchestrator remained in the `CREATE_ORDER` step despite events being sent to Kafka. This was happening because there was a naming mismatch between the Kafka topics defined in the services and the actual topics being used by the test script and Kafka.

- Services (e.g., saga orchestrator) were using underscore format: `order_events`, `user_events`
- Kafka topics and test script were using hyphen format: `order-events`, `user-events`

Due to this inconsistency, events were published to hyphenated topics (e.g., `order-events`), but services were subscribing to topics with underscores (e.g., `order_events`), causing events to not be received by the services.

## Changes Made

1. Updated the comprehensive test script to use underscore format for topics:
   ```python
   "order_events_topic": "order_events",
   "user_events_topic": "user_events",
   # ...and so on for all topics
   ```

2. Updated the Kafka topic configuration in `kafka/config/topics.json` to use underscore format:
   ```json
   {
     "name": "order_events",
     "partitions": 3,
     "replicationFactor": 1,
     ...
   }
   ```

3. Added missing command topics and timer events topic to the Kafka configuration:
   - `user_commands`
   - `order_commands`
   - `payment_commands`
   - `timer_commands`
   - `timer_events`

4. Checked and updated topic names in all microservices:
   - **Timer Service** - Updated references to `timer-events` to `timer_events` in:
     - `app/__init__.py` config defaults
     - `app/api/timer_routes.py` - all instances using `KAFKA_TOPIC_TIMER_EVENTS` 

   - **Notification Service** - Updated `poll_service.py` to use underscore format for all topics:
     - Changed topics list from hyphenated to underscore format
     - Added command topics to monitoring list

   - **User Service** - Already using underscore format

   - **Payment Service** - Already using underscore format

   - **Order Service** - Already using underscore format

## Technical Explanation

Kafka topics need to have consistent naming across the entire system. When the services and test scripts use different names, the events don't reach their intended recipients, as they're effectively using different channels.

By standardizing on the underscore format (`order_events` instead of `order-events`), we ensure that all parts of the system are using the same topic names.

## Next Steps

1. Restart Kafka and all services to apply the topic configuration changes:
   ```
   docker-compose down
   docker-compose up -d
   ```

2. Run the comprehensive test script to verify the fixes:
   ```
   cd services/create-order-saga-orchestrator && python comprehensive_test.py --docker
   ```

3. Monitor the logs of the create-order-saga-orchestrator to see if it properly processes events:
   ```
   docker-compose logs -f create-order-saga-orchestrator
   ```

4. Check if the saga state progresses beyond the `CREATE_ORDER` step when events are published.
