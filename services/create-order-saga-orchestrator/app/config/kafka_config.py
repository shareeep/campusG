import os

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

# Kafka topics for commands
ORDER_COMMANDS_TOPIC = 'order_commands'
PAYMENT_COMMANDS_TOPIC = 'payment_commands'
TIMER_COMMANDS_TOPIC = 'timer_commands'
USER_COMMANDS_TOPIC = 'user_commands'

# Kafka topics for events
ORDER_EVENTS_TOPIC = 'order_events'
PAYMENT_EVENTS_TOPIC = 'payment_events'
TIMER_EVENTS_TOPIC = 'timer_events'
USER_EVENTS_TOPIC = 'user_events'

# Consumer group ID
CONSUMER_GROUP_ID = 'create-order-saga-orchestrator'
