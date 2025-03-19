import json
from datetime import datetime
from flask import current_app
from kafka import KafkaConsumer
from app import db
from app.models.system_log import SystemLog

class LogConsumer:
    """Consumer that reads log messages from Kafka and stores them in the database"""
    
    def __init__(self, bootstrap_servers=None, topic='system-logs', group_id='payment-log-consumer'):
        """
        Initialize the log consumer
        
        Args:
            bootstrap_servers (str, optional): Kafka bootstrap servers
            topic (str, optional): Kafka topic to consume from
            group_id (str, optional): Consumer group ID
        """
        self.bootstrap_servers = bootstrap_servers or current_app.config.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic = topic
        self.group_id = group_id
        self._consumer = None
        self.running = False
    
    @property
    def consumer(self):
        """Lazy-loaded KafkaConsumer instance"""
        if self._consumer is None:
            self._consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
        return self._consumer
    
    def start(self):
        """Start consuming logs from Kafka"""
        self.running = True
        current_app.logger.info(f"Starting log consumer for topic {self.topic}")
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    # Process the log message
                    self._process_log(message.value)
                except Exception as e:
                    current_app.logger.error(f"Error processing log message: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Error in log consumer: {str(e)}")
        finally:
            self.close()
    
    def _process_log(self, log_data):
        """
        Process a log message from Kafka and store it in the database
        
        Args:
            log_data (dict): Log data from Kafka
        """
        try:
            # Check if this is our own service's log or from another service
            service = log_data.get('service', 'unknown')
            
            # Convert timestamp to datetime
            timestamp = datetime.fromisoformat(log_data['timestamp'])
            
            # Create log record
            log = SystemLog(
                timestamp=timestamp,
                level=log_data['level'],
                message=log_data['message'],
                trace_id=log_data.get('traceId'),
                request_id=log_data.get('requestId'),
                data=log_data.get('data')
            )
            
            # Save to database
            db.session.add(log)
            db.session.commit()
            
            current_app.logger.debug(f"Stored log from {service} with ID {log.id}")
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to store log in database: {str(e)}")
    
    def stop(self):
        """Stop the consumer"""
        self.running = False
    
    def close(self):
        """Close the consumer connection"""
        if self._consumer:
            self._consumer.close()
            self._consumer = None

# Function to start the log consumer in a background thread
def start_log_consumer_thread(app):
    """
    Start the log consumer in a background thread
    
    Args:
        app: Flask application context
    """
    import threading
    
    def run_consumer():
        with app.app_context():
            consumer = LogConsumer()
            consumer.start()
    
    # Start consumer in a background thread
    thread = threading.Thread(target=run_consumer, daemon=True)
    thread.start()
    
    return thread
