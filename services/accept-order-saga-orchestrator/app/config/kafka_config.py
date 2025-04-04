import os

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

# Kafka topics for commands (specific to accept order saga)
ACCEPT_ORDER_COMMANDS_TOPIC = os.getenv('ACCEPT_ORDER_COMMANDS_TOPIC', 'accept_order_commands')

# Kafka topics for events (specific to accept order saga)
ACCEPT_ORDER_EVENTS_TOPIC = os.getenv('ACCEPT_ORDER_EVENTS_TOPIC', 'accept_order_events')

# Consumer group ID for the Accept Order Saga orchestrator
CONSUMER_GROUP_ID = os.getenv('ACCEPT_ORDER_CONSUMER_GROUP_ID', 'accept-order-saga-orchestrator')
