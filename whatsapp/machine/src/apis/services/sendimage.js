import { getAllSessions, getSession } from '../../whatsapp.js';
import { sleep } from '../../utils/config.js';

function detectMimeType(base64String) {
  if (base64String.includes('image/png')) return 'image/png';
  if (base64String.includes('image/webp')) return 'image/webp';
  return 'image/jpeg';
}

export async function sendImage(req, res) {
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
      imageUrl: m.imageUrl,
      caption: m.caption || ""
    }));
  } else if (req.body.messages && Array.isArray(req.body.messages)) {
    waUsers = req.body.messages.map(m => ({
      jid: m.jid,
      imageUrl: m.imageUrl,
      caption: m.caption || ""
    }));
  } else {
    waUsers = [{
      jid: req.body.jid,
      imageUrl: req.body.imageUrl,
      caption: req.body.caption || ""
    }];
  }

  const data = [];

  for (const user of waUsers) {

    if (!user || !user.imageUrl) {
      data.push({
        jid: user?.jid ?? 'unknown',
        error: "Field 'imageUrl' wajib"
      });
      continue;
    }

    try {
      const isBase64 = user.imageUrl.startsWith("data:image");

      let imagePayload;

      if (isBase64) {
        const mimeType = detectMimeType(user.imageUrl);
        const base64Data = user.imageUrl.split(',')[1];

        imagePayload = {
          image: Buffer.from(base64Data, 'base64'),
          mimetype: mimeType
        };

      } else {
        imagePayload = {
          image: { url: user.imageUrl },
          mimetype: "image/jpeg"
        };
      }

      await sock.sendMessage(user.jid, {
        ...imagePayload,
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
