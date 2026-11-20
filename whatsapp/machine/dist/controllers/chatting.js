import {
  getSession,
  getAllSessions,
  toJid,
  SessionStatus,
  saveMessageToStore,
  getQuotedMessage,
} from '../whatsapp.js';

/**
 * Helper untuk mendapatkan sesi aktif yang valid (dengan fallback pintar)
 */
function resolveWorkingSession(requestedSession) {
  const allSessions = getAllSessions();
  if (allSessions.length === 0) return null;

  // 1. Coba match langsung
  if (requestedSession) {
    const direct = getSession(requestedSession);
    if (direct && direct.status === SessionStatus.WORKING && direct.sock) {
      return direct;
    }
  }

  // 2. Coba cari sesi pertama yang berstatus WORKING
  for (const name of allSessions) {
    const s = getSession(name);
    if (s && s.status === SessionStatus.WORKING && s.sock) {
      return s;
    }
  }

  // 3. Fallback ke sesi pertama yang terdaftar
  return getSession(allSessions[0]);
}

/**
 * Helper untuk mengekstrak atau menyusun objek quoted message (WhatsApp contextInfo)
 */
function resolveQuoted(item, jid) {
  if (!item) return undefined;

  // 1. Jika objek quoted WAMessage sudah lengkap disertakan
  const quoted = item.quoted;
  if (quoted && typeof quoted === 'object' && quoted.key) {
    return quoted;
  }

  // 2. Jika diberikan ID pesan yang dibalas (reply_to, replyTo, quotedMessageId, messageId, reply)
  const replyTo =
    item.reply_to ||
    item.replyTo ||
    item.quotedMessageId ||
    item.quotedMsg ||
    item.reply ||
    item.messageId;

  if (replyTo && typeof replyTo === 'string') {
    return getQuotedMessage(replyTo.trim(), jid);
  }

  return undefined;
}

/**
 * Controller untuk pengiriman pesan teks ala WAHA (POST /api/sendText)
 * Mendukung format WAHA: { session, chatId, text, reply_to }
 * Mendukung format Array: [{ session, outbox_for, message, reply_to }, ...]
 * Sekaligus fleksibel untuk fallback { phone, to, message, _botDevice, jid, outbox_for }
 */
export async function sendText(req, res) {
  try {
    const items = Array.isArray(req.body) ? req.body : [req.body];
    if (items.length === 0 || !items[0]) {
      return res.status(400).json({ error: 'Body request tidak boleh kosong.' });
    }

    const allResults = [];

    for (const item of items) {
      const requestedSession = item.session || item._botDevice || item.name;
      const session = resolveWorkingSession(requestedSession);

      if (!session || session.status !== SessionStatus.WORKING || !session.sock) {
        return res.status(400).json({
          error: `Sesi '${requestedSession || 'default'}' belum siap atau belum terhubung (status: ${session?.status || 'NOT_FOUND'}).`,
        });
      }

      const rawChatId = item.chatId || item.jid || item.phone || item.to || item.outbox_for || item.recipient;
      const text = item.text ?? item.message;

      if (!rawChatId) {
        return res.status(400).json({ error: "Field 'chatId' atau 'outbox_for' wajib diisi." });
      }
      if (text === undefined || text === null || text === '') {
        return res.status(400).json({ error: "Field 'text' atau 'message' wajib diisi." });
      }

      // Normalisasi list nomor tujuan (bisa array, bisa string dipisah koma)
      let targetList = [];
      if (Array.isArray(rawChatId)) {
        targetList = rawChatId;
      } else if (typeof rawChatId === 'string' && rawChatId.includes(',')) {
        targetList = rawChatId.split(',').map(s => s.trim()).filter(Boolean);
      } else {
        targetList = [rawChatId];
      }

      const sock = session.sock;

      for (const target of targetList) {
        const jid = toJid(target);
        if (!jid) continue;

        // Siapkan opsi reply / quote jika ada
        const quotedMsg = resolveQuoted(item, jid);
        const sendOptions = quotedMsg ? { quoted: quotedMsg } : {};

        try {
          const sent = await sock.sendMessage(jid, { text: String(text) }, sendOptions);

          // Simpan ke store agar jika WhatsApp meminta retry handshake, bot bisa membalas
          if (sent?.key?.id && sent?.message) {
            saveMessageToStore(sent.key.id, sent.message, sent.key);
          }

          allResults.push({
            success: true,
            id: sent.key.id,
            to: jid,
            timestamp: sent.messageTimestamp,
          });
        } catch (sendErr) {
          allResults.push({
            success: false,
            to: jid,
            error: sendErr.message,
          });
        }
      }
    }

    // Jika hanya 1 pesan ke 1 nomor dan bukan array di root
    if (!Array.isArray(req.body) && allResults.length === 1) {
      const single = allResults[0];
      return single.success ? res.status(200).json(single) : res.status(500).json(single);
    }

    // Jika multiple
    return res.status(200).json({
      success: allResults.some(r => r.success),
      total: allResults.length,
      results: allResults,
    });
  } catch (err) {
    console.error('sendText error:', err);
    return res.status(500).json({ error: `Gagal mengirim pesan: ${err.message}` });
  }
}

/**
 * Controller untuk pengiriman reply pesan ala WAHA / Erpro (POST /api/reply atau POST /api/sendReply)
 * Mendukung body: { session, phone/chatId, message/text, messageId/reply_to }
 */
export async function reply(req, res) {
  const body = req.body || {};
  const messageId =
    body.messageId ||
    body.reply_to ||
    body.replyTo ||
    body.quotedMessageId ||
    body.quotedMsg;

  if (!messageId) {
    return res.status(400).json({ error: "Field 'messageId' atau 'reply_to' wajib diisi untuk melakukan reply." });
  }

  req.body.reply_to = messageId;
  return sendText(req, res);
}

/**
 * Controller untuk pengiriman gambar ala WAHA (POST /api/sendImage)
 */
export async function sendImage(req, res) {
  try {
    const sessionName = req.body.session || req.body._botDevice || req.body.name;
    const session = resolveWorkingSession(sessionName);
    if (!session || session.status !== SessionStatus.WORKING || !session.sock) {
      return res.status(400).json({ error: `Sesi '${sessionName || 'default'}' belum terhubung.` });
    }

    const rawChatId = req.body.chatId || req.body.jid || req.body.phone || req.body.to || req.body.outbox_for;
    if (!rawChatId) {
      return res.status(400).json({ error: "Field 'chatId' wajib diisi." });
    }

    const jid = toJid(rawChatId);
    const caption = req.body.caption || '';
    const fileUrl = req.body.file?.url || req.body.url || req.body.image;

    if (!fileUrl) {
      return res.status(400).json({ error: "Field 'file.url' atau 'url' wajib diisi." });
    }

    let imagePayload = {};
    if (typeof fileUrl === 'string' && fileUrl.startsWith('http')) {
      imagePayload = { image: { url: fileUrl }, caption };
    } else if (typeof fileUrl === 'string' && fileUrl.startsWith('data:image')) {
      const buffer = Buffer.from(fileUrl.split(',')[1], 'base64');
      imagePayload = { image: buffer, caption };
    } else {
      imagePayload = { image: { url: fileUrl }, caption };
    }

    const quotedMsg = resolveQuoted(req.body, jid);
    const sendOptions = quotedMsg ? { quoted: quotedMsg } : {};

    const sent = await session.sock.sendMessage(jid, imagePayload, sendOptions);
    if (sent?.key?.id && sent?.message) {
      saveMessageToStore(sent.key.id, sent.message, sent.key);
    }

    return res.status(200).json({
      success: true,
      id: sent.key.id,
      to: jid,
      timestamp: sent.messageTimestamp,
    });
  } catch (err) {
    console.error('sendImage error:', err);
    return res.status(500).json({ error: `Gagal mengirim gambar: ${err.message}` });
  }
}

/**
 * Controller untuk pengiriman file / dokumen ala WAHA (POST /api/sendFile)
 */
export async function sendFile(req, res) {
  try {
    const sessionName = req.body.session || req.body._botDevice || req.body.name;
    const session = resolveWorkingSession(sessionName);
    if (!session || session.status !== SessionStatus.WORKING || !session.sock) {
      return res.status(400).json({ error: `Sesi '${sessionName || 'default'}' belum terhubung.` });
    }

    const rawChatId = req.body.chatId || req.body.jid || req.body.phone || req.body.to || req.body.outbox_for;
    if (!rawChatId) {
      return res.status(400).json({ error: "Field 'chatId' wajib diisi." });
    }

    const jid = toJid(rawChatId);
    const caption = req.body.caption || '';
    const fileUrl = req.body.file?.url || req.body.url || req.body.document;
    const filename = req.body.file?.filename || req.body.filename || 'document';
    const mimetype = req.body.file?.mimetype || req.body.mimetype || 'application/octet-stream';

    if (!fileUrl) {
      return res.status(400).json({ error: "Field 'file.url' atau 'url' wajib diisi." });
    }

    const documentPayload = {
      document: { url: fileUrl },
      mimetype,
      fileName: filename,
      caption,
    };

    const quotedMsg = resolveQuoted(req.body, jid);
    const sendOptions = quotedMsg ? { quoted: quotedMsg } : {};

    const sent = await session.sock.sendMessage(jid, documentPayload, sendOptions);
    if (sent?.key?.id && sent?.message) {
      saveMessageToStore(sent.key.id, sent.message, sent.key);
    }

    return res.status(200).json({
      success: true,
      id: sent.key.id,
      to: jid,
      timestamp: sent.messageTimestamp,
    });
  } catch (err) {
    console.error('sendFile error:', err);
    return res.status(500).json({ error: `Gagal mengirim dokumen: ${err.message}` });
  }
}
