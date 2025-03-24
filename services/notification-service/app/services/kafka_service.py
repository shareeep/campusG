# Completely detached no-op Kafka client

class KafkaClient:
    """No-op Kafka client that does nothing"""
    
    def __init__(self, bootstrap_servers=None):
        """
        Initialize the client (no-op)
        """
        pass
    
    def publish(self, topic, message):
        """
        Pretend to publish a message (no-op)
        
        Returns:
            bool: Always True
        """
        return True
    
    def close(self):
        """No-op close method"""
        pass

# Global Kafka client instance
kafka_client = KafkaClient()
