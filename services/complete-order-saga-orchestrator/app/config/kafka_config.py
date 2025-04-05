import os

# Kafka configuration for the Complete Order Saga
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

# Kafka topic for commands related to completing orders
COMPLETE_ORDER_COMMANDS_TOPIC = os.getenv('COMPLETE_ORDER_COMMANDS_TOPIC', 'complete_order_commands')

# Kafka topic for events from the complete order saga
COMPLETE_ORDER_EVENTS_TOPIC = os.getenv('COMPLETE_ORDER_EVENTS_TOPIC', 'complete_order_events')

# Consumer group ID for the complete order saga orchestrator
CONSUMER_GROUP_ID = os.getenv('COMPLETE_ORDER_CONSUMER_GROUP_ID', 'complete-order-saga-orchestrator')
