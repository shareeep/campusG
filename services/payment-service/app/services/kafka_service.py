# Completely detached no-op Kafka client

class KafkaService:
    """No-op Kafka service that does nothing"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KafkaService, cls).__new__(cls)
            cls._instance.is_connected = False
        return cls._instance
        
    def connect(self):
        """Pretend to connect to Kafka broker"""
        self.is_connected = True
        return True
            
    def disconnect(self):
        """Pretend to disconnect from Kafka broker"""
        self.is_connected = False
        return True
            
    def publish(self, topic, message):
        """Pretend to publish a message to a Kafka topic"""
        # We don't actually publish anything
        return True
            
    def subscribe(self, topic, callback, from_beginning=False):
        """Pretend to subscribe to a Kafka topic"""
        # We don't actually subscribe to anything
        pass
            
    def _delivery_report(self, err, msg):
        """Mock callback for message delivery reports"""
        pass

# Singleton instance
kafka_client = KafkaService()
