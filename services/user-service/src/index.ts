import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { PrismaClient } from '@prisma/client';
import config from './config';
import userRoutes from './routes/userRoutes';
import kafkaClient from './services/kafkaService';

// Initialize Express app
const app = express();
const prisma = new PrismaClient();

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/users', userRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

// Error handling middleware
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// Start the server
const PORT = config.port;
app.listen(PORT, () => {
  console.log(`User service running on port ${PORT}`);
  
  // Connect to Kafka
  kafkaClient.connect()
    .then(() => {
      console.log('Connected to Kafka');
      
      // Subscribe to relevant topics
      kafkaClient.subscribe('user-events');
    })
    .catch(err => {
      console.error('Failed to connect to Kafka:', err);
    });
});

// Handle graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM signal received: closing HTTP server');
  await prisma.$disconnect();
  await kafkaClient.disconnect();
  process.exit(0);
});

export default app;
