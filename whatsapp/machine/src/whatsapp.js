import { makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion, DisconnectReason } from '@whiskeysockets/baileys';
import pino from 'pino';
import fs from 'fs';
import path from 'path';
import { deleteSessionFolder } from './utils/config.js';
import axios from 'axios';
import { exec } from 'child_process';
import { promisify } from 'util';
import WebSocket from 'ws';

const sessions = new Map();

const djangoWs = new WebSocket('ws://127.0.0.1:8000/ws/whatsapp/webhook/');
djangoWs.on('open', () => console.log('✅ Connected to Django WebSocket'));
djangoWs.on('error', (err) => console.error('❌ Django WS Error:', err.message));
djangoWs.on('close', () => console.log('⚠️ Django WS Connection Closed.'));

export async function connectToWhatsApp(phoneNumber) {
  const sessionDir = path.resolve(`./src/sessions/${phoneNumber}`);
  if (!fs.existsSync(sessionDir)) fs.mkdirSync(sessionDir, { recursive: true });

  const { state, saveCreds } = await useMultiFileAuthState(sessionDir);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    logger: pino({ level: 'silent' }),
    printQRInTerminal: false,
    browser: ['Ubuntu', 'Chrome', '20.0.04'],
    auth: state,
    version,
    getMessage: async () => ({}),
  });

  sessions.set(phoneNumber, { sock, state, latestQR: null });

  // Simpan credentials secara otomatis
  sock.ev.on('creds.update', saveCreds);

  // Event koneksi dan QR
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;
    const session = sessions.get(phoneNumber);

    if (!session) return;

    if (qr) {
      session.latestQR = qr;
      console.log(`[${phoneNumber}] QR baru diterima`);
    }

    if (connection === 'open') {
      console.log(`[${phoneNumber}] Bot terhubung`);
      session.latestQR = null; // bersihkan QR setelah connect
    }

    if (connection === 'close') {
	  const statusCode = lastDisconnect?.error?.output?.statusCode;

	  if (statusCode === 401) {
		console.log(`[${phoneNumber}] Session expired. Harus scan ulang.`);
		deleteSessionFolder(phoneNumber); // hapus folder sesi lama
	  } else {
		console.log(`[${phoneNumber}] Reconnecting...`);
		setTimeout(() => connectToWhatsApp(phoneNumber), 5000);
	  }
	}

    if (qr && djangoWs.readyState === WebSocket.OPEN) {
        djangoWs.send(JSON.stringify({
            event: 'connection.qrcode',
            session: session,
            data: { qr: qr }
        }));
    }

  });

  // Handler pesan masuk
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
	  if (type !== 'notify') return;

	  const msg = messages[0];
	  if (!msg.message) return;
	  if (msg.key.fromMe) return;

	  const sender = msg.key.remoteJid;
	  const text =
		msg.message?.extendedTextMessage?.text ||
		msg.message?.conversation ||
		msg.message?.imageMessage?.caption ||
		msg.message?.videoMessage?.caption ||
		msg.message?.buttonsResponseMessage?.selectedButtonId ||
		msg.message?.templateButtonReplyMessage?.selectedId ||
		msg.message?.listResponseMessage?.singleSelectReply?.selectedRowId ||
		msg.message?.extendedTextMessage?.contextInfo?.quotedMessage?.conversation ||
		'';

	  const messageType = Object.keys(msg.message)[0];

	try {
		  const session = sessions.get(phoneNumber);
		  const payload = {
            event: 'messages.upsert',
            session: phoneNumber,
            data: {
                messages: [msg]
            },
            metadata: {
                phone: phoneNumber,
                sender: msg.key.remoteJid,
                push_name: msg.pushName,
                text: msg.message?.extendedTextMessage?.text || msg.message?.conversation || '',
                message_type: messageType
            },
			bot_device: {
			  phone: phoneNumber,
			  user: session?.user || null,
			  platform: 'whatsapp',
			  connected: !!session,
			  last_connection: new Date().toISOString(),
			},
			message_id: msg.key.id,
			sender: msg.key.remoteJid,
			push_name: msg.pushName,
			timestamp: msg.messageTimestamp,
			message_type: messageType,
			text:
			  msg.message.extendedTextMessage?.text ||
			  msg.message.conversation ||
			  '',
			raw: msg
		  };
		  const payloadSize = Buffer.byteLength(JSON.stringify(payload), 'utf8');

          if (djangoWs.readyState === WebSocket.OPEN) {
            djangoWs.send(JSON.stringify(payload));
          }
		  /*console.log(`[${phoneNumber}] Pesan dari ${sender}: ${JSON.stringify(payload, null, 2)}`);*/

		  if (text.trim().toLowerCase() === 'ping') {
			await sock.sendMessage(sender, 
				{ text: 'pong 🏓', },
				{ quoted: msg, }
			);
			return;
		  } else if (text.trim().toLowerCase().includes('tiktok.com')) {
			await handleTiktok(sock, sender, msg, text)
			return;
		  } else if (text.trim().toLowerCase().includes('instagram.com')) {
			await handleInstagram(sock, sender, msg, text)
			return;
		  } else if (text.trim().toLowerCase().includes('youtu.be')) {
			await handleYoutube(sock, sender, msg, text)
			return;
		  } else {
			await sock.sendMessage(sender,{ 
				text: 'Tunggu sebentar...' ,
			},{ 
				quoted: msg, 
			});
			return;
		  }
	} catch (err) {
		  console.error(`error: ${err?.message || err}`);
	}
	  
  });

  return sessions.get(phoneNumber);
}

export function getSession(phoneNumber) {
  return sessions.get(phoneNumber);
}

export function getAllSessions() {
  return [...sessions.keys()];
}

export async function handleTiktok(sock, sender, msg, url) {
    try {
		await sock.sendMessage(sender,{ 
			text: 'Tunggu sebentar...' ,
		},{ 
			quoted: msg, 
		});
        const api = `https://www.tikwm.com/api/?url=${encodeURIComponent(url)}`;
        const { data } = await axios.get(api);

        if (!data.data) {
            return await sock.sendMessage(sender,{ 
				text: 'Gagal mengambil video' ,
			},{ 
				quoted: msg, 
			});
        }

        const videoUrl = data.data.play;

        await sock.sendMessage(sender, {
            video: { 
				url: videoUrl,
			}, caption: 'Berhasil download TikTok 🎥'
		},{
			quoted: msg 
		});

    } catch (err) {
        console.log(err)
        await sock.sendMessage(msg.key.remoteJid, {
            text: 'Terjadi kesalahan saat mengambil video.'
        });
    }
}

export async function handleInstagram(sock, sender, msg, url) {
    try {

        await sock.sendMessage(sender, { 
            text: 'Tunggu sebentar...' 
        }, { 
            quoted: msg 
        });

        const api = `https://snapinsta.ai/download?url=${encodeURIComponent(url)}`
        const response = await fetch(api)

        const contentType = response.headers.get("content-type")
        if (!contentType || !contentType.includes("application/json")) {
            const html = await response.text()
            console.log("API RETURN HTML:", html.substring(0, 300))

            return await sock.sendMessage(sender, {
                text: 'API Instagram sedang bermasalah.'
            }, { quoted: msg })
        }

        const data = await response.json()

        if (!data.result || data.result.length === 0) {
            return await sock.sendMessage(sender, { 
                text: 'Gagal mengambil media Instagram.' 
            }, { quoted: msg });
        }

        for (let media of data.result) {

            if (media.type === 'video') {
                await sock.sendMessage(sender, {
                    video: { url: media.url },
                    caption: 'Berhasil download Instagram 🎥'
                }, {
                    quoted: msg
                });

            } 
            else {
                await sock.sendMessage(sender, {
                    image: { url: media.url },
                    caption: 'Berhasil download Instagram 🖼'
                }, {
                    quoted: msg
                });

            }
        }

    } catch (err) {
        console.log("IG ERROR:", err)

        await sock.sendMessage(sender, {
            text: 'Terjadi kesalahan saat mengambil Instagram.'
        }, {
            quoted: msg
        });
    }
}

export async function handleYoutube(sock, sender, msg, url) {
    try {
		const execAsync = promisify(exec);
        await sock.sendMessage(sender, {
            text: 'Tunggu sebentar, sedang mengambil video...'
        }, { 
			quoted: msg 
		});

        const ytdlpPath = 'C:\\Microservice.Erp\\bin\\yt-dlp.exe';

        const command = `"${ytdlpPath}" -f "mp4[height<=720]" -g "${url}"`;

        const { stdout } = await execAsync(command);

        const videoUrl = stdout.trim().split('\n')[0];

        if (!videoUrl) {
            throw new Error('Video URL tidak ditemukan');
        }

        await sock.sendMessage(sender, {
            video: { 
				url: videoUrl 
			},caption: 'Berhasil download YouTube 🎬'
        }, { 
			quoted: msg 
		});

    } catch (err) {
        console.log('YT ERROR:', err)

        await sock.sendMessage(sender, {
            text: 'Gagal mengambil video YouTube.'
        }, { 
			quoted: msg 
		});
    }
}