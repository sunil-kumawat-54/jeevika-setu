import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import router from './routes/api.routes';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5001;

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Request logging middleware
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'online',
    service: 'KaushalVani Backend API Gateway',
    timestamp: new Date().toISOString(),
    version: '1.0.0-MVP'
  });
});

// Register API routes
app.use('/api', router);

// Handle 404
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

app.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(`   KAUSHALVANI BACKEND SERVER RUNNING ON PORT ${PORT}`);
  console.log(`   Health Check: http://localhost:${PORT}/health`);
  console.log(`   API Endpoint: http://localhost:${PORT}/api/beneficiaries`);
  console.log(`====================================================`);
});
