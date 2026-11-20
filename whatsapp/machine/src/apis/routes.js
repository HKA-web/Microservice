import { Router } from 'express';

// Controller standar WAHA & Reply (Single Source of Truth)
import { sendText, sendImage, sendFile, reply } from '../controllers/chatting.js';
import {
  getSessions,
  startSessionHandler,
  stopSessionHandler,
  logoutSessionHandler,
  getQrCodeHandler,
} from '../controllers/sessions.js';

const router = Router();

/* ========================================================
 * 1. STANDAR CHATTING & REPLY API (Single Truth)
 * ======================================================== */
router.post('/sendText', sendText);
router.post('/sendImage', sendImage);
router.post('/sendFile', sendFile);

// Endpoint Reply ala Erpro & WAHA
router.post('/reply', reply);
router.post('/sendReply', reply);
router.post('/message/reply', reply);
router.post('/:session/message/reply', (req, res, next) => {
  req.body = req.body || {};
  req.body.session = req.params.session;
  return reply(req, res, next);
});

/* ========================================================
 * 2. STANDAR WAHA SESSION MANAGEMENT API
 * ======================================================== */
router.get('/sessions', getSessions);
router.post('/sessions', startSessionHandler);
router.post('/sessions/start', startSessionHandler);
router.post('/sessions/stop', stopSessionHandler);
router.post('/sessions/logout', logoutSessionHandler);

// Endpoint QR Code (mendukung pola WAHA /api/{session}/auth/qr dan /api/sessions/{session}/auth/qr)
router.get('/:session/auth/qr', getQrCodeHandler);
router.get('/sessions/:session/auth/qr', getQrCodeHandler);

export default router;
