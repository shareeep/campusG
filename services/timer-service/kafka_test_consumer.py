#!/usr/bin/env python3
from kafka import KafkaConsumer
import json
import sys
import signal
import datetime

def signal_handler(sig, frame):
    print("\nShutting down consumer...")
    sys.exit(0)

def start_consumer(topic='timer-events', bootstrap_servers='localhost:9092'):
    """
    Start a Kafka consumer that prints messages from the specified topic
    
    Args:
        topic: Kafka topic to consume from
        bootstrap_servers: Kafka bootstrap servers
    """
    print(f"Starting Kafka consumer for topic: {topic}")
    print(f"Connected to Kafka at: {bootstrap_servers}")
    print("Press Ctrl+C to exit")
    
    try:
        # Create consumer
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='latest',  # Start from latest messages
            enable_auto_commit=True,
            group_id=f'test-consumer-{datetime.datetime.now().timestamp()}',  # Unique group ID
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        print("\nConsumer started. Waiting for messages...")
        
        # Process messages
        for message in consumer:
            print(f"\n--- New Message at {datetime.datetime.now().isoformat()} ---")
            print(f"Topic: {message.topic}")
            print(f"Partition: {message.partition}")
            print(f"Offset: {message.offset}")
            print(f"Timestamp: {datetime.datetime.fromtimestamp(message.timestamp/1000)}")
            print(f"Value: {json.dumps(message.value, indent=2)}")

    except KeyboardInterrupt:
        print("\nShutting down consumer...")
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        try:
            consumer.close()
        except:
            pass
        
        print("Consumer closed")

if __name__ == "__main__":
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get bootstrap servers from command line if provided
    bootstrap_servers = sys.argv[1] if len(sys.argv) > 1 else 'localhost:9092'
    
    # Get topic from command line if provided
    topic = sys.argv[2] if len(sys.argv) > 2 else 'timer-events'
    
    # Start consumer
    start_consumer(topic, bootstrap_servers)
