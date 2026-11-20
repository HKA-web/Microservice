import express from 'express';
import fs from 'fs';
import path from 'path';
import multer from 'multer';
import swaggerUi from 'swagger-ui-express';
import bodyParser from 'body-parser';
import cors from 'cors';
import os from 'os';
import { initSessionsFromDisk } from './whatsapp.js';
import route from './apis/routes.js';

const app = express();
const upload = multer();

// CORS supaya bisa diakses IP luar
app.use(cors({ origin: '*', methods: ['GET', 'POST', 'PUT', 'DELETE'], allowedHeaders: ['Content-Type', 'Authorization'] }));

// Endpoint raw openapi.json (selalu membaca file terbaru dari disk tanpa cache)
const swaggerFilePath = path.join(process.cwd(), 'openapi.json');
app.get('/openapi.json', (req, res) => {
  res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
  res.set('Pragma', 'no-cache');
  res.set('Expires', '0');
  if (fs.existsSync(swaggerFilePath)) {
    res.sendFile(swaggerFilePath);
  } else {
    res.status(404).json({ error: 'openapi.json tidak ditemukan' });
  }
});

// Swagger Docs (Mengambil spec dinamis dari /openapi.json)
app.use(
  '/docs',
  (req, res, next) => {
    res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    res.set('Pragma', 'no-cache');
    res.set('Expires', '0');
    next();
  },
  swaggerUi.serve,
  swaggerUi.setup(null, { swaggerUrl: '/openapi.json' })
);

// Middleware
app.use(bodyParser.json());
app.use(express.urlencoded({ extended: true }));
app.use(upload.none());

// Root redirect ke Swagger Docs
app.get('/', (req, res) => res.redirect('/docs'));

// Single Source of Truth API Routes
app.use('/api', route);

// Auto reconnect sesi yang tersimpan di disk
initSessionsFromDisk();

function getLocalIP() {
  const nets = os.networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      if (net.family === 'IPv4' && !net.internal) return net.address;
    }
  }
  return '0.0.0.0';
}

const portArg = process.argv.find(arg => arg.startsWith('--port='));
const webhookArg = process.argv.find(arg => arg.startsWith('--webhook.url='));
if (webhookArg && !process.env.WEBHOOK_URL) {
  process.env.WEBHOOK_URL = webhookArg.split('=')[1];
}

const PORT = process.env.PORT || (portArg ? portArg.split('=')[1] : null) || 3002;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`🚀 WAHA Microservice berjalan di port: ${PORT}`);
  console.log(`Local:        http://localhost:${PORT}`);
  console.log(`Network:      http://${getLocalIP()}:${PORT}`);
  console.log(`Swagger Docs: http://localhost:${PORT}/docs`);
  if (process.env.WEBHOOK_URL) {
    console.log(`Webhook URL:  ${process.env.WEBHOOK_URL}`);
  }
});
