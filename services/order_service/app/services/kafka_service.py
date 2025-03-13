from confluent_kafka import Producer, Consumer, KafkaError
import json
import logging
from flask import current_app
import uuid

class KafkaService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KafkaService, cls).__new__(cls)
            cls._instance.producer = None
            cls._instance.consumer = None
            cls._instance.is_connected = False
        return cls._instance
        
    def connect(self):
        """Connect to Kafka broker"""
        try:
            # Initialize producer
            producer_config = {
                'bootstrap.servers': current_app.config['KAFKA_BROKERS'],
                'client.id': current_app.config['KAFKA_CLIENT_ID']
            }
            self.producer = Producer(producer_config)
            
            # Initialize consumer
            consumer_config = {
                'bootstrap.servers': current_app.config['KAFKA_BROKERS'],
                'group.id': current_app.config['KAFKA_GROUP_ID'],
                'auto.offset.reset': 'earliest'
            }
            self.consumer = Consumer(consumer_config)
            
            self.is_connected = True
            current_app.logger.info("Connected to Kafka")
            return True
        except Exception as e:
            current_app.logger.error(f"Error connecting to Kafka: {str(e)}")
            return False
            
    def disconnect(self):
        """Disconnect from Kafka broker"""
        try:
            if self.producer:
                self.producer.flush()
            
            if self.consumer:
                self.consumer.close()
                
            self.is_connected = False
            current_app.logger.info("Disconnected from Kafka")
            return True
        except Exception as e:
            current_app.logger.error(f"Error disconnecting from Kafka: {str(e)}")
            return False
            
    def publish(self, topic, message):
        """Publish a message to a Kafka topic"""
        if not self.is_connected or not self.producer:
            raise Exception("Kafka producer not connected")
            
        try:
            # Convert message to JSON string and encode as bytes
            message_bytes = json.dumps(message).encode('utf-8')
            
            # Publish message to Kafka topic
            self.producer.produce(
                topic=topic,
                value=message_bytes,
                key=str(uuid.uuid4()).encode('utf-8'),
                callback=self._delivery_report
            )
            
            # Flush to ensure the message is sent
            self.producer.flush()
            
            current_app.logger.info(f"Published message to topic {topic}")
            return True
        except Exception as e:
            current_app.logger.error(f"Error publishing message to topic {topic}: {str(e)}")
            raise e
            
    def subscribe(self, topic, callback, from_beginning=False):
        """Subscribe to a Kafka topic"""
        if not self.is_connected or not self.consumer:
            raise Exception("Kafka consumer not connected")
            
        try:
            # Subscribe to the topic
            self.consumer.subscribe([topic])
            
            # Start consuming messages
            while True:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        current_app.logger.info(f"Reached end of partition for topic {topic}")
                    else:
                        current_app.logger.error(f"Error while consuming from topic {topic}: {msg.error()}")
                else:
                    # Process the message
                    try:
                        value = json.loads(msg.value().decode('utf-8'))
                        callback(topic, value)
                    except Exception as e:
                        current_app.logger.error(f"Error processing message from topic {topic}: {str(e)}")
                        
        except Exception as e:
            current_app.logger.error(f"Error subscribing to topic {topic}: {str(e)}")
            raise e
            
    def _delivery_report(self, err, msg):
        """Callback for message delivery reports"""
        if err is not None:
            current_app.logger.error(f"Message delivery failed: {str(err)}")
        else:
            current_app.logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

# Singleton instance
kafka_client = KafkaService()
