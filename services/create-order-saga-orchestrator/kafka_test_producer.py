#!/usr/bin/env python
"""
Kafka test producer for simulating events from other services.
Useful for testing the saga orchestrator's handling of events.
"""

import json
import uuid
import argparse
from datetime import datetime
from kafka import KafkaProducer
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define Kafka topics
ORDER_EVENTS_TOPIC = 'order_events'
USER_EVENTS_TOPIC = 'user_events'
PAYMENT_EVENTS_TOPIC = 'payment_events'
TIMER_EVENTS_TOPIC = 'timer_events'

# Define event templates
EVENT_TEMPLATES = {
    'order.created': {
        'topic': ORDER_EVENTS_TOPIC,
        'payload': {
            'order_id': str(uuid.uuid4()),
            'customer_id': 'customer123',
            'status': 'PENDING_PAYMENT'
        }
    },
    'order.status_updated': {
        'topic': ORDER_EVENTS_TOPIC,
        'payload': {
            'order_id': None,  # To be filled in during execution
            'status': 'CREATED'
        }
    },
    'user.payment_info_retrieved': {
        'topic': USER_EVENTS_TOPIC,
        'payload': {
            'payment_info': {
                'card_type': 'visa',
                'last_four': '4242',
                'card_token': 'tok_visa'
            }
        }
    },
    'payment.authorized': {
        'topic': PAYMENT_EVENTS_TOPIC,
        'payload': {
            'payment_id': str(uuid.uuid4()),
            'order_id': None,  # To be filled in during execution
            'amount': 25.99,
            'status': 'AUTHORIZED'
        }
    },
    'timer.started': {
        'topic': TIMER_EVENTS_TOPIC,
        'payload': {
            'order_id': None,  # To be filled in during execution
            'timeout_at': (datetime.utcnow().isoformat()),
            'status': 'RUNNING'
        }
    },
    'order.creation_failed': {
        'topic': ORDER_EVENTS_TOPIC,
        'payload': {
            'error': 'Failed to create order in database'
        }
    },
    'user.payment_info_failed': {
        'topic': USER_EVENTS_TOPIC,
        'payload': {
            'error': 'User payment info not found'
        }
    },
    'payment.failed': {
        'topic': PAYMENT_EVENTS_TOPIC,
        'payload': {
            'error': 'Payment authorization failed - insufficient funds'
        }
    },
    'order.status_update_failed': {
        'topic': ORDER_EVENTS_TOPIC,
        'payload': {
            'order_id': None,  # To be filled in during execution
            'error': 'Failed to update order status'
        }
    },
    'timer.failed': {
        'topic': TIMER_EVENTS_TOPIC,
        'payload': {
            'order_id': None,  # To be filled in during execution
            'error': 'Failed to start timer'
        }
    }
}

def send_event(producer, topic, event_type, correlation_id, payload):
    """Send a single event to Kafka"""
    message = {
        'type': event_type,
        'correlation_id': correlation_id,
        'timestamp': datetime.utcnow().isoformat(),
        'payload': payload
    }
    
    logger.info(f"Sending {event_type} to {topic} with correlation_id {correlation_id}")
    
    # Send message and get metadata
    future = producer.send(topic, message)
    try:
        record_metadata = future.get(timeout=10)
        logger.info(f"Message delivered to {record_metadata.topic} [{record_metadata.partition}]")
    except Exception as e:
        logger.error(f"Message delivery failed: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Kafka test producer for saga events')
    parser.add_argument('--bootstrap-servers', default='localhost:9092', help='Kafka bootstrap servers')
    parser.add_argument('--correlation-id', default=None, help='Correlation ID to use (saga ID)')
    parser.add_argument('--event', required=True, choices=list(EVENT_TEMPLATES.keys()), help='Event type to send')
    parser.add_argument('--order-id', default=None, help='Order ID to use in the payload')
    
    args = parser.parse_args()
    
    # Create correlation ID if not provided
    correlation_id = args.correlation_id or str(uuid.uuid4())
    
    # Configure Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    # Get event template
    event_template = EVENT_TEMPLATES[args.event]
    topic = event_template['topic']
    payload = event_template['payload'].copy()
    
    # Update payload with provided order_id if applicable
    if args.order_id and 'order_id' in payload:
        payload['order_id'] = args.order_id
    
    # Send the event
    send_event(producer, topic, args.event, correlation_id, payload)
    
    # Flush to ensure message is sent before exiting
    producer.flush()
    
    logger.info(f"Event {args.event} sent to topic {topic}")

if __name__ == "__main__":
    main()
