import { getAllSessions, getSession } from '../../whatsapp.js';
import { sendChunk, sleep } from '../../utils/config.js';

export async function sendMessage(req, res) {
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
    waUsers = req.body.map(m => ({ jid: m.jid, message: m.message }));
  } else if (req.body.messages && Array.isArray(req.body.messages)) {
    waUsers = req.body.messages.map(m => ({ jid: m.jid, message: m.message }));
  } else {
    waUsers = [{ jid: req.body.jid, message: req.body.message }];
  }

  const data = [];

  for (const user of waUsers) {
    if (!user || !user.message) {
      data.push({ jid: user?.jid ?? 'unknown', error: "Field 'message' wajib" });
      continue;
    }

    try {
      await sendChunk(
		  String(user.message).replace(/\\n/g, '\n'),
		  async (batchText) => {
			const sendResult = await sock.sendMessage(user.jid, { text: batchText });

			data.push({
			  jid: user.jid,
			  error: null,
			});
		}
	  );
      await sleep();
    } catch (err) {
      data.push({ jid: user.jid, error: err?.message || String(err) });
    }
  }

  res.json({ data });
}
