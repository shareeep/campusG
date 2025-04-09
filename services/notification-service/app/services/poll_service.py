"""
Poll-based Kafka service for the Notification Service.
This module implements a polling approach to consume messages from Kafka
and save them to the database.
"""

import json
import logging
import os
from datetime import datetime
from kafka import KafkaConsumer, TopicPartition
from app import db
from app.models.models import Notifications, KafkaOffsets

# Configure logging
logger = logging.getLogger(__name__)

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
CONSUMER_GROUP_ID = 'notification-service-group'
KAFKA_POLL_INTERVAL_SECONDS = int(os.getenv('KAFKA_POLL_INTERVAL_SECONDS', '10'))

# Topics to monitor
KAFKA_TOPICS = [
    "user_events", 
    "order_events", 
    "payment_events", 
    "escrow_events", 
    "timer_events",
    "notification_events",
    # Command topics
    "order_commands",
    "user_commands",
    "payment_commands",
    "timer_commands"
]

def get_stored_offsets():
    """Retrieve the latest consumed offsets from the database."""
    offsets = {}
    stored_offsets = KafkaOffsets.query.all()
    
    for offset in stored_offsets:
        if offset.topic not in offsets:
            offsets[offset.topic] = {}
        offsets[offset.topic][offset.partition] = offset.offset
        
    return offsets

def update_stored_offset(topic, partition, offset):
    """Update the stored offset for a topic-partition."""
    stored_offset = KafkaOffsets.query.filter_by(
        topic=topic, 
        partition=partition
    ).first()
    
    if stored_offset:
        stored_offset.offset = offset
        stored_offset.updated_at = datetime.utcnow()
    else:
        stored_offset = KafkaOffsets(
            topic=topic,
            partition=partition,
            offset=offset
        )
        db.session.add(stored_offset)
        
    db.session.commit()

def poll_kafka_once():
    """
    Poll Kafka once for new messages and save them to the database.
    Returns the number of messages processed.
    """
    logger.info("Starting Kafka polling cycle")
    messages_processed = 0
    
    try:
        # Get stored offsets
        stored_offsets = get_stored_offsets()
        logger.debug(f"Retrieved stored offsets: {stored_offsets}")
        
        # Create consumer without subscribing yet
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP_ID,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
        )
        
        # Get partition metadata for all topics
        topics_metadata = consumer.topics()
        logger.debug(f"Available Kafka topics: {topics_metadata}")
        
        # Ensure our topics exist 
        existing_topics = [topic for topic in KAFKA_TOPICS if topic in topics_metadata]
        if not existing_topics:
            logger.warning(f"None of the configured topics exist: {KAFKA_TOPICS}")
            consumer.close()
            return 0
            
        # Get partitions for each topic
        partitions = []
        for topic in existing_topics:
            topic_partitions = consumer.partitions_for_topic(topic)
            if not topic_partitions:
                logger.warning(f"No partitions found for topic {topic}")
                continue
                
            for partition in topic_partitions:
                tp = TopicPartition(topic, partition)
                
                # If we have a stored offset, seek to it + 1
                if (topic in stored_offsets and 
                        partition in stored_offsets[topic]):
                    offset = stored_offsets[topic][partition] + 1
                    consumer.assign([tp])
                    consumer.seek(tp, offset)
                    logger.debug(f"Seeking to offset {offset} for {topic}:{partition}")
                
                partitions.append(tp)
                
        # Assign all partitions
        consumer.assign(partitions)
        logger.info(f"Assigned {len(partitions)} partitions across {len(existing_topics)} topics")
        
        # Poll for messages
        poll_results = consumer.poll(timeout_ms=5000, max_records=500)
        logger.info(f"Polled Kafka and got results for {len(poll_results)} topic-partitions")
        
        # Process messages
        for tp, messages in poll_results.items():
            topic = tp.topic
            partition = tp.partition
            logger.info(f"Processing {len(messages)} messages from {topic}:{partition}")
            
            for message in messages:
                try:
                    # Extract message data
                    message_data = message.value
                    if isinstance(message_data, str):
                        try:
                            message_data = json.loads(message_data)
                        except json.JSONDecodeError:
                            message_data = {"event": message_data}
                    
                    event_type = message_data.get('type', 'unknown')
                    payload = message_data.get('payload', message_data)
                    correlation_id = message_data.get('correlation_id', '')
                    source_service = message_data.get('source', 'unknown')
                    
                    # Extract IDs with fallbacks for different naming conventions
                    customer_id = str(payload.get('customer_id', payload.get('customerId', '')))
                    runner_id = str(payload.get('runner_id', payload.get('runnerId', '')))
                    order_id = str(payload.get('order_id', payload.get('orderId', '')))
                    status_ = str(payload.get('status', payload.get('status', '')))
                    
                    # Format event info
                    event_info = {
                        'topic': topic,
                        'event_type': event_type,
                        'correlation_id': correlation_id,
                        'source_service': source_service,
                        'timestamp': datetime.utcnow().isoformat(),
                        'payload': payload
                    }
                    
                    # Replace the existing "Create notification" block with this:
                    existing_notification = Notifications.query.filter_by(
                        correlation_id=correlation_id,
                        event_type=event_type,
                        source_topic=topic
                    ).first()

                    if not existing_notification:
                        notification = Notifications(
                            customer_id=customer_id if customer_id not in ('None', 'null', '') else '',
                            runner_id=runner_id if runner_id not in ('None', 'null', '') else None,
                            order_id=order_id if order_id not in ('None', 'null', '') else '',
                            event=json.dumps(event_info),
                            status=status_ if status_ not in ('None', 'null', '') else None,
                            source_topic=topic,
                            event_type=event_type,
                            correlation_id=correlation_id,
                            source_service=source_service
                        )
                        
                        db.session.add(notification)
                        messages_processed += 1
                    else:
                        logger.debug(f"Skipping duplicate notification: {correlation_id}, {event_type}")

                    # Still update the offset regardless
                    update_stored_offset(topic, partition, message.offset)

                    logger.debug(f"Processed message from {topic} with event type {event_type}")
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    db.session.rollback()
                
            # Commit session after processing batch for partition
            # Replace your existing commit block with this:
            try:
                db.session.commit()
                logger.info(f"Committed {messages_processed} notifications to database")
            except Exception as e:
                if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                    logger.info("Duplicate records detected and skipped")
                    db.session.rollback()
                    # Still need to update offsets even if we skipped duplicates
                    db.session.commit()
                else:
                    logger.error(f"Error committing session: {e}", exc_info=True)
                    db.session.rollback()
                
        consumer.close()
        logger.info(f"Kafka polling cycle completed, processed {messages_processed} messages")
        return messages_processed
        
    except Exception as e:
        logger.error(f"Error in poll_kafka_once: {e}", exc_info=True)
        return 0

def run_periodic_poll():
    """
    Function to run in a non-daemon thread that polls at regular intervals.
    This should be called in a background thread.
    """
    import time
    import sys
    
    logger.info(f"Starting periodic Kafka polling every {KAFKA_POLL_INTERVAL_SECONDS} seconds")
    
    # Import here to avoid circular imports
    from app import create_app
    
    # Create a dedicated Flask app instance for the polling thread
    app = create_app()
    
    while True:
        try:
            with app.app_context():
                messages = poll_kafka_once()
                logger.info(f"Polling cycle processed {messages} messages")
        except Exception as e:
            logger.error(f"Error in polling cycle: {e}", exc_info=True)
            # Try recreating the app context if we had an error
            try:
                app = create_app()
                logger.info("Recreated Flask application context")
            except Exception as app_error:
                logger.error(f"Failed to recreate app context: {app_error}", exc_info=True)
            
        # Sleep until next poll
        time.sleep(KAFKA_POLL_INTERVAL_SECONDS)
