import dotenv from 'dotenv';

// Load environment variables from .env file
dotenv.config();

const config = {
  // Server configuration
  port: process.env.PORT || 3000,
  nodeEnv: process.env.NODE_ENV || 'development',

  // Kafka configuration
  kafka: {
    clientId: 'user-service',
    brokers: (process.env.KAFKA_BROKERS || 'localhost:9092').split(','),
    groupId: 'user-service-group',
  },

  // Clerk Authentication
  clerk: {
    apiKey: process.env.CLERK_API_KEY,
  },
  
  // Service URLs
  services: {
    orderService: process.env.ORDER_SERVICE_URL || 'http://localhost:3002',
    paymentService: process.env.PAYMENT_SERVICE_URL || 'http://localhost:3003',
  },
};

export default config;
