import { getAllSessions, getSession } from '../../whatsapp.js';
import { sleep } from '../../utils/config.js';

export async function sendVideo(req, res) {
  const allSessions = getAllSessions();
  if (!allSessions || allSessions.length === 0) {
    return res.status(500).json({ error: 'Tidak ada device WA aktif' });
  }

  const deviceId = req.body._botDevice;

  const session = deviceId
    ? getSession(deviceId)
    : getSession(allSessions[0]);

  if (!session) return res.status(400).json({ error: 'Device tidak ditemukan' });
  if (!session.sock) return res.status(500).json({ error: 'Socket WA belum siap' });

  const sock = session.sock;

  let waUsers = [];

  if (Array.isArray(req.body)) {
    waUsers = req.body.map(m => ({
      jid: m.jid,
      videoUrl: m.videoUrl,
      caption: m.caption || ""
    }));
  } else if (req.body.messages && Array.isArray(req.body.messages)) {
    waUsers = req.body.messages.map(m => ({
      jid: m.jid,
      videoUrl: m.videoUrl,
      caption: m.caption || ""
    }));
  } else {
    waUsers = [{
      jid: req.body.jid,
      videoUrl: req.body.videoUrl,
      caption: req.body.caption || ""
    }];
  }

  const data = [];

  for (const user of waUsers) {
    if (!user || !user.videoUrl) {
      data.push({ jid: user?.jid ?? 'unknown', error: "Field 'videoUrl' wajib" });
      continue;
    }

    try {
      await sock.sendMessage(user.jid, {
        video: { url: user.videoUrl },
        caption: String(user.caption).replace(/\\n/g, '\n')
      });

      data.push({
        jid: user.jid,
        error: null,
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
