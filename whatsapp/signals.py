import json
import logging
from django import dispatch
from django.dispatch import receiver
from prodict import Prodict
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from whatsapp import utils, settings
from datetime import datetime
from django.utils.timezone import make_aware

logger = logging.getLogger(__name__)

webhook = dispatch.Signal()


@receiver(webhook)
def on_qrcode(sender, request, **kwargs):
    try:
        body = Prodict.from_dict(json.loads(request.body))
        if body.event == 'connection.qrcode':
            session_id = body.session
            qr_data = body.data.qr

            logger.info(f"✨ [QR RECEIVED] Session: {session_id} | QR: {qr_data[:20]}...")

            layer = get_channel_layer()
            async_to_sync(layer.group_send)(
                f"session.{session_id}",
                {"type": "send.data", "data": json.dumps({'qrcode': qr_data})}
            )
    except Exception as e:
        logger.error(f"Error on_qrcode: {e}")

@receiver(webhook)
def on_connection_status(sender, request, **kwargs):
    try:
        body = Prodict.from_dict(json.loads(request.body))
        if body.event in ('connection.open', 'connection.close'):
            status = "CONNECTED" if body.event == 'connection.open' else "DISCONNECTED"
            logger.info(f"🌐 [STATUS] Session {body.session} is {status}")
    except Exception as e:
        logger.error(f"Error on_connection_status: {e}")


@receiver(webhook)
def on_inbox(sender, request, **kwargs):
    try:
        data_json = json.loads(request.body)

        if data_json.get('event') == 'messages.upsert':
            # Ambil session dan pastikan jadi string tanpa spasi
            session_id = str(data_json.get('session')).strip()

            # Ambil data dari root atau metadata (berdasarkan print data_json Anda)
            push_name = data_json.get('push_name') or "Unknown"
            message_text = data_json.get('text') or ""

            logger.info(f"🚀 Memancarkan ke grup: session.{session_id} | Dari: {push_name}")

            layer = get_channel_layer()
            async_to_sync(layer.group_send)(
                f"session.{session_id}",
                {
                    "type": "send.data",
                    "data": json.dumps({
                        "type": "new_message",
                        "content": {
                            "push_name": push_name,
                            "text": message_text
                        }
                    })
                }
            )
    except Exception as e:
        logger.error(f"❌ Error Signal on_inbox: {e}")