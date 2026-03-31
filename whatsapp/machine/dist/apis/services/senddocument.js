import { getAllSessions, getSession } from '../../whatsapp.js';
import { sleep } from '../../utils/config.js';
import path from 'path';

function detectMimeType(base64String, filename = '') {
  if (base64String?.includes('application/pdf') || filename.endsWith('.pdf'))
    return 'application/pdf';

  if (filename.endsWith('.doc'))
    return 'application/msword';

  if (filename.endsWith('.docx'))
    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

  if (filename.endsWith('.xlsx'))
    return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

  if (filename.endsWith('.xls'))
    return 'application/vnd.ms-excel';

  return 'application/octet-stream';
}

export async function sendDocument(req, res) {
  const allSessions = getAllSessions();
  if (!allSessions || allSessions.length === 0) {
    return res.status(500).json({ error: 'Tidak ada device WA aktif' });
  }

  const deviceId = req.body._botDevice;

  const session = deviceId
    ? getSession(deviceId)
    : getSession(allSessions[0]);

  if (!session) {
    return res.status(400).json({ error: 'Device tidak ditemukan' });
  }

  if (!session.sock) {
    return res.status(500).json({ error: 'Socket WA belum siap' });
  }

  const sock = session.sock;

  let waUsers = [];

  if (Array.isArray(req.body)) {
    waUsers = req.body.map(m => ({
      jid: m.jid,
      documentUrl: m.documentUrl,
      fileName: m.fileName || "document",
      caption: m.caption || ""
    }));
  } else if (req.body.messages && Array.isArray(req.body.messages)) {
    waUsers = req.body.messages.map(m => ({
      jid: m.jid,
      documentUrl: m.documentUrl,
      fileName: m.fileName || "document",
      caption: m.caption || ""
    }));
  } else {
    waUsers = [{
      jid: req.body.jid,
      documentUrl: req.body.documentUrl,
      fileName: req.body.fileName || "document",
      caption: req.body.caption || ""
    }];
  }

  const data = [];

  for (const user of waUsers) {

    if (!user || !user.documentUrl) {
      data.push({
        jid: user?.jid ?? 'unknown',
        error: "Field 'documentUrl' wajib"
      });
      continue;
    }

    try {
      const isBase64 = user.documentUrl.startsWith("data:");

      let documentPayload;

      if (isBase64) {
        const base64Data = user.documentUrl.split(',')[1];
        const mimeType = detectMimeType(user.documentUrl, user.fileName);

        documentPayload = {
          document: Buffer.from(base64Data, 'base64'),
          mimetype: mimeType,
          fileName: user.fileName
        };

      } else {
        const ext = path.extname(user.fileName);
        const mimeType = detectMimeType(null, user.fileName);

        documentPayload = {
          document: { url: user.documentUrl },
          mimetype: mimeType,
          fileName: user.fileName || `file${ext}`
        };
      }

      await sock.sendMessage(user.jid, {
        ...documentPayload,
        caption: String(user.caption).replace(/\\n/g, '\n')
      });

      data.push({
        jid: user.jid,
        error: null
      });

      await sleep();

    } catch (err) {
      data.push({
        jid: user.jid,
        error: err?.message || String(err)
      });
    }
  }

  res.json({ data });
}
