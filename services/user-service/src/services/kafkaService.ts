import { Kafka, Consumer, Producer } from 'kafkajs';
import config from '../config';

class KafkaService {
  private kafka: Kafka;
  private producer: Producer | null = null;
  private consumer: Consumer | null = null;
  private isConnected = false;

  constructor() {
    this.kafka = new Kafka({
      clientId: config.kafka.clientId,
      brokers: config.kafka.brokers,
    });
  }

  async connect(): Promise<void> {
    try {
      // Initialize producer
      this.producer = this.kafka.producer();
      await this.producer.connect();

      // Initialize consumer
      this.consumer = this.kafka.consumer({ 
        groupId: config.kafka.groupId 
      });
      await this.consumer.connect();

      this.isConnected = true;
    } catch (error) {
      console.error('Error connecting to Kafka:', error);
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    try {
      if (this.producer) {
        await this.producer.disconnect();
      }
      if (this.consumer) {
        await this.consumer.disconnect();
      }
      this.isConnected = false;
    } catch (error) {
      console.error('Error disconnecting from Kafka:', error);
      throw error;
    }
  }

  async publish(topic: string, message: any): Promise<void> {
    if (!this.isConnected || !this.producer) {
      throw new Error('Kafka producer not connected');
    }

    try {
      await this.producer.send({
        topic,
        messages: [
          { 
            value: JSON.stringify(message) 
          },
        ],
      });
    } catch (error) {
      console.error(`Error publishing message to topic ${topic}:`, error);
      throw error;
    }
  }

  async subscribe(topic: string, fromBeginning: boolean = false): Promise<void> {
    if (!this.isConnected || !this.consumer) {
      throw new Error('Kafka consumer not connected');
    }

    try {
      await this.consumer.subscribe({ 
        topic,
        fromBeginning
      });

      await this.consumer.run({
        eachMessage: async ({ topic, partition, message }) => {
          try {
            const value = message.value?.toString();
            if (value) {
              const parsedMessage = JSON.parse(value);
              console.log(`Received message from topic ${topic}:`, parsedMessage);
              // Process message based on topic and content
              this.processMessage(topic, parsedMessage);
            }
          } catch (error) {
            console.error(`Error processing message from topic ${topic}:`, error);
          }
        },
      });
    } catch (error) {
      console.error(`Error subscribing to topic ${topic}:`, error);
      throw error;
    }
  }

  private processMessage(topic: string, message: any): void {
    // Add custom message processing logic based on topics
    switch (topic) {
      case 'user-events':
        // Handle user events
        break;
      case 'order-events':
        // Handle order-related events that might affect users
        break;
      default:
        console.log(`No specific handler for topic ${topic}`);
    }
  }
}

// Export a singleton instance
const kafkaClient = new KafkaService();
export default kafkaClient;
