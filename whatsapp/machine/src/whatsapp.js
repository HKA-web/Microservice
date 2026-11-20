import {
  makeWASocket,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  DisconnectReason,
  Browsers,
} from '@whiskeysockets/baileys';
import pino from 'pino';
import fs from 'fs';
import path from 'path';
import axios from 'axios';
import WebSocket from 'ws';
import { deleteSessionFolder } from './utils/config.js';

// Cache sederhana untuk retry counter dan message store Baileys (anti "Waiting for this message")
class SimpleCache {
  constructor(maxSize = 3000) {
    this.map = new Map();
    this.maxSize = maxSize;
  }
  get(key) {
    return this.map.get(key);
  }
  set(key, value) {
    if (this.map.size >= this.maxSize) {
      const firstKey = this.map.keys().next().value;
      this.map.delete(firstKey);
    }
    this.map.set(key, value);
    return true;
  }
  del(key) {
    return this.map.delete(key);
  }
  has(key) {
    return this.map.has(key);
  }
}

// Session Folder Root
const sessionRoot = path.resolve('./src/sessions');
if (!fs.existsSync(sessionRoot)) {
  fs.mkdirSync(sessionRoot, { recursive: true });
}

const messageStore = new SimpleCache(5000);
const retryCache = new SimpleCache(2000);
const messageKeyStore = new SimpleCache(5000);

// Disk persistence untuk message store agar tidak hilang saat restart
const messageStoreFile = path.resolve(sessionRoot, 'message_store.json');
let diskStore = {};
try {
  if (fs.existsSync(messageStoreFile)) {
    diskStore = JSON.parse(fs.readFileSync(messageStoreFile, 'utf-8'));
    console.log(`[Store] Memuat ${Object.keys(diskStore).length} pesan dari cache disk.`);
  }
} catch (e) {
  diskStore = {};
}

let saveTimeout = null;
function scheduleSaveDiskStore() {
  if (saveTimeout) return;
  saveTimeout = setTimeout(() => {
    saveTimeout = null;
    try {
      const keys = Object.keys(diskStore);
      if (keys.length > 5000) {
        for (let i = 0; i < keys.length - 5000; i++) {
          delete diskStore[keys[i]];
        }
      }
      fs.writeFileSync(messageStoreFile, JSON.stringify(diskStore), 'utf-8');
    } catch (err) {
      console.error('[Store] Gagal menyimpan message store ke disk:', err.message);
    }
  }, 1000);
}

export function saveMessageToStore(id, message, key = null) {
  if (id && message) {
    messageStore.set(id, message);
    diskStore[id] = message;
    if (key) {
      messageKeyStore.set(id, key);
    }
    scheduleSaveDiskStore();
  }
}

export function getMessageFromStore(id) {
  if (!id) return undefined;
  return messageStore.get(id) || diskStore[id] || undefined;
}

export function getQuotedMessage(id, fallbackJid = null) {
  if (!id) return null;
  const msgContent = getMessageFromStore(id);
  const key = messageKeyStore.get(id) || {
    remoteJid: fallbackJid,
    fromMe: false,
    id: id,
  };
  return {
    key,
    message: msgContent || { conversation: '' },
  };
}

// Status Enum ala WAHA
export const SessionStatus = {
  STARTING: 'STARTING',
  SCAN_QR_CODE: 'SCAN_QR_CODE',
  WORKING: 'WORKING',
  FAILED: 'FAILED',
  STOPPED: 'STOPPED',
};

// In-Memory Session Store
const sessions = new Map();

// ==========================================
// Webhook & Django WebSocket Integration
// ==========================================
const webhookHttp = process.env.WEBHOOK_URL || 'http://127.0.0.1:8008/whatsapp/webhook/';
const wsUrl = webhookHttp
  .replace(/^http/, 'ws')
  .replace(/\/whatsapp\/webhook\/?$/, '/ws/whatsapp/webhook/');

let djangoWs = null;
let wsReconnectTimer = null;

function connectDjangoWs() {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }

  try {
    djangoWs = new WebSocket(wsUrl);

    djangoWs.on('open', () => {
      console.log('✅ Connected to Django WebSocket at ' + wsUrl);
    });

    djangoWs.on('error', (err) => {
      // console.error('❌ Django WS Error:', err.message);
    });

    djangoWs.on('close', () => {
      if (!wsReconnectTimer) {
        wsReconnectTimer = setTimeout(connectDjangoWs, 3000);
      }
    });
  } catch (err) {
    if (!wsReconnectTimer) {
      wsReconnectTimer = setTimeout(connectDjangoWs, 3000);
    }
  }
}
connectDjangoWs();

export function sendToDjango(payload) {
  // 1. Kirim via WebSocket jika terhubung
  if (djangoWs && djangoWs.readyState === WebSocket.OPEN) {
    try {
      djangoWs.send(typeof payload === 'string' ? payload : JSON.stringify(payload));
      return true;
    } catch (err) {
      console.error('❌ Gagal kirim ke Django WS:', err.message);
    }
  }

  // 2. Fallback kirim via HTTP POST jika ada endpoint HTTP webhook
  if (webhookHttp && !webhookHttp.startsWith('ws:')) {
    axios.post(webhookHttp, payload, { timeout: 3000 }).catch(() => {
      // diamkan jika Django belum menyediakan HTTP view
    });
  }
  return false;
}

// ==========================================
// Helper Format JID / Nomor HP
// ==========================================
export function toJid(input) {
  if (!input) return '';
  let str = String(input).trim();

  // Sudah format JID WhatsApp
  if (str.includes('@s.whatsapp.net') || str.includes('@g.us') || str.includes('@lid')) {
    return str;
  }

  // Format grup
  if (str.includes('-') && !str.startsWith('+')) {
    return `${str}@g.us`;
  }

  // Bersihkan karakter non-digit
  let cleaned = str.replace(/\D/g, '');

  // Ubah awalan lokal 08xxx menjadi 628xxx
  if (cleaned.startsWith('0')) {
    cleaned = '62' + cleaned.substring(1);
  }

  return `${cleaned}@s.whatsapp.net`;
}

// ==========================================
// Session Manager Functions (WAHA Style)
// ==========================================

export async function startSession(sessionId) {
  if (!sessionId) throw new Error('sessionId wajib diisi.');

  const sessionName = String(sessionId).trim();
  const existing = sessions.get(sessionName);

  // Jika sudah aktif/working, kembalikan instance yang ada
  if (existing && existing.status === SessionStatus.WORKING && existing.sock) {
    return existing;
  }

  const sessionDir = path.resolve(sessionRoot, sessionName);
  if (!fs.existsSync(sessionDir)) {
    fs.mkdirSync(sessionDir, { recursive: true });
  }

  console.log(`[${sessionName}] Memulai sesi WhatsApp...`);

  const sessionObj = {
    name: sessionName,
    status: SessionStatus.STARTING,
    sock: null,
    qr: null,
    latestQR: null,
    user: null,
    updatedAt: new Date(),
    isStopped: false,
    reconnectAttempts: 0,
  };
  sessions.set(sessionName, sessionObj);

  try {
    const { state, saveCreds } = await useMultiFileAuthState(sessionDir);
    const { version } = await fetchLatestBaileysVersion().catch(() => ({ version: [2, 3000, 1015901307] }));

    const sock = makeWASocket({
      logger: pino({ level: 'silent' }),
      printQRInTerminal: false,
      browser: Browsers.ubuntu('Chrome'),
      auth: state,
      version,
      syncFullHistory: false,
      msgRetryCounterCache: retryCache,
      getMessage: async (key) => {
        const id = key?.id;
        if (!id) return undefined;

        let cached = getMessageFromStore(id);
        if (cached) {
          console.log(`🔄 [RETRY HANDSHAKE] Menemukan pesan di store lokal untuk ID: ${id}`);
          return cached;
        }

        // Fallback: Query ke endpoint Sent di Django untuk merekonstruksi pesan teks jika server baru direstart
        try {
          const res = await axios.get(`http://127.0.0.1:8008/whatsapp/api/sent/${id}/`, { timeout: 3000 });
          if (res.data && res.data.message) {
            const rawMsg = res.data.message;
            let text = rawMsg;
            try {
              const parsed = JSON.parse(rawMsg);
              if (parsed && typeof parsed === 'object') {
                text = parsed.text || parsed.message || parsed.body || rawMsg;
              }
            } catch (_) {}

            const reconstructed = { conversation: String(text) };
            saveMessageToStore(id, reconstructed);
            console.log(`🔄 [RETRY HANDSHAKE] Berhasil mengambil pesan dari Django Sent API untuk ID: ${id}`);
            return reconstructed;
          }
        } catch (_) {
          // Abaikan jika tidak ditemukan di database
        }

        console.log(`⚠️ [RETRY HANDSHAKE] Pesan tidak ditemukan untuk ID: ${id}`);
        return undefined;
      },
    });

    sessionObj.sock = sock;

    // Simpan credentials otomatis
    sock.ev.on('creds.update', saveCreds);

    // Event Koneksi & QR Code
    sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;
      sessionObj.updatedAt = new Date();

      if (qr) {
        sessionObj.status = SessionStatus.SCAN_QR_CODE;
        sessionObj.qr = qr;
        sessionObj.latestQR = qr;
        console.log(`[${sessionName}] QR Code siap di-scan.`);

        // Kirim event webhook
        sendToDjango({
          event: 'session.status',
          session: sessionName,
          status: SessionStatus.SCAN_QR_CODE,
          data: { qr },
        });
        // Kompatibilitas signal Django lama
        sendToDjango({
          event: 'connection.qrcode',
          session: sessionName,
          data: { qr },
        });
      }

      if (connection === 'open') {
        sessionObj.status = SessionStatus.WORKING;
        sessionObj.qr = null;
        sessionObj.latestQR = null;
        sessionObj.user = sock.user;
        sessionObj.reconnectAttempts = 0;
        console.log(`[${sessionName}] WhatsApp terhubung! User:`, sock.user?.id || sock.user?.name);

        sendToDjango({
          event: 'session.status',
          session: sessionName,
          status: SessionStatus.WORKING,
          data: { user: sock.user },
        });
        // Kompatibilitas signal Django lama
        sendToDjango({
          event: 'connection.open',
          session: sessionName,
          data: { user: sock.user },
        });
      }

      if (connection === 'close') {
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        console.log(`[${sessionName}] Koneksi terputus. Kode status:`, statusCode);

        if (statusCode === DisconnectReason.loggedOut || statusCode === 401) {
          sessionObj.status = SessionStatus.STOPPED;
          sessionObj.isStopped = true;
          sessionObj.qr = null;
          console.log(`[${sessionName}] Sesi telah logout / kadaluarsa.`);
          deleteSessionFolder(sessionName);
          sessions.delete(sessionName);

          sendToDjango({
            event: 'session.status',
            session: sessionName,
            status: SessionStatus.STOPPED,
          });
          sendToDjango({
            event: 'connection.close',
            session: sessionName,
            data: { reason: 'logged_out', statusCode },
          });
        } else if (!sessionObj.isStopped) {
          sessionObj.status = SessionStatus.FAILED;
          sessionObj.reconnectAttempts += 1;
          const delay = Math.min(sessionObj.reconnectAttempts * 2000, 10000);
          console.log(`[${sessionName}] Mencoba menghubungkan kembali dalam ${delay / 1000}s...`);

          setTimeout(() => {
            if (!sessionObj.isStopped) {
              startSession(sessionName).catch(err => {
                console.error(`[${sessionName}] Gagal reconnect:`, err.message);
              });
            }
          }, delay);

          sendToDjango({
            event: 'session.status',
            session: sessionName,
            status: SessionStatus.FAILED,
          });
          sendToDjango({
            event: 'connection.close',
            session: sessionName,
            data: { reason: 'disconnected', statusCode },
          });
        }
      }
    });

    // Handler Pesan Masuk (Inbound Message)
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
      // Simpan semua pesan ke store untuk keperluan retry handshake & reply quote
      for (const m of (messages || [])) {
        if (m?.key?.id && m?.message) {
          saveMessageToStore(m.key.id, m.message, m.key);
        }
      }

      if (type !== 'notify') return;

      const msg = messages[0];
      if (!msg || !msg.message) return;
      if (msg.key.fromMe) return;

      const sender = msg.key.remoteJid;
      const text =
        msg.message?.extendedTextMessage?.text ||
        msg.message?.conversation ||
        msg.message?.imageMessage?.caption ||
        msg.message?.videoMessage?.caption ||
        msg.message?.documentMessage?.caption ||
        '';

      const messageType = Object.keys(msg.message)[0] || 'conversation';

      const payload = {
        event: 'messages.upsert',
        waha_event: 'message',
        session: sessionName,
        payload: {
          id: msg.key.id,
          from: sender,
          pushName: msg.pushName || 'Unknown',
          body: text,
          type: messageType,
          timestamp: msg.messageTimestamp,
          raw: msg,
        },
        // Fallback properti untuk backward compatibility dengan Django signal on_inbox lama
        data: { messages: [msg] },
        metadata: {
          phone: sessionName,
          sender: sender,
          push_name: msg.pushName,
          text: text,
          message_type: messageType,
        },
        from_me: false,
        message_id: msg.key.id,
        sender: sender,
        push_name: msg.pushName,
        timestamp: msg.messageTimestamp,
        message_type: messageType,
        text: text,
        raw: msg,
      };

      sendToDjango(payload);
      // Kirim event format WAHA standar jika ada consumer eksternal
      sendToDjango({
        ...payload,
        event: 'message',
      });
    });

    return sessionObj;
  } catch (err) {
    sessionObj.status = SessionStatus.FAILED;
    console.error(`[${sessionName}] Gagal memulai sesi:`, err.message);
    throw err;
  }
}

export async function stopSession(sessionId) {
  const sessionName = String(sessionId).trim();
  const session = sessions.get(sessionName);

  if (!session) {
    return { success: false, message: 'Sesi tidak ditemukan atau belum aktif.' };
  }

  session.isStopped = true;
  session.status = SessionStatus.STOPPED;
  session.qr = null;

  if (session.sock) {
    try {
      session.sock.end(undefined);
    } catch (_) {}
  }

  sendToDjango({
    event: 'session.status',
    session: sessionName,
    status: SessionStatus.STOPPED,
  });

  return { success: true, message: `Sesi ${sessionName} berhasil dihentikan.` };
}

export async function logoutSession(sessionId) {
  const sessionName = String(sessionId).trim();
  const session = sessions.get(sessionName);

  if (session && session.sock) {
    try {
      await session.sock.logout();
    } catch (_) {}
    try {
      session.sock.end(undefined);
    } catch (_) {}
  }

  deleteSessionFolder(sessionName);
  sessions.delete(sessionName);

  sendToDjango({
    event: 'session.status',
    session: sessionName,
    status: SessionStatus.STOPPED,
  });

  return { success: true, message: `Sesi ${sessionName} berhasil logout dan dihapus.` };
}

export function getSession(sessionId) {
  const sessionName = String(sessionId).trim();
  return sessions.get(sessionName);
}

export function listSessions() {
  const list = [];
  for (const [name, s] of sessions.entries()) {
    list.push({
      name: s.name,
      status: s.status,
      user: s.user,
      hasQr: !!s.qr,
      updatedAt: s.updatedAt,
    });
  }
  return list;
}

// Auto-Reconnection semua sesi yang ada di folder saat startup
export async function initSessionsFromDisk() {
  if (!fs.existsSync(sessionRoot)) return;

  const entries = fs.readdirSync(sessionRoot, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory()) {
      const sessionName = entry.name;
      console.log(`[Auto-Start] Memuat sesi tersimpan: ${sessionName}...`);
      try {
        await startSession(sessionName);
        await new Promise(r => setTimeout(r, 1500));
      } catch (err) {
        console.error(`[Auto-Start] Gagal memuat sesi ${sessionName}:`, err.message);
      }
    }
  }
}

// Backward compatibility export untuk fungsi lama
export const connectToWhatsApp = startSession;
export function getAllSessions() {
  return [...sessions.keys()];
}
