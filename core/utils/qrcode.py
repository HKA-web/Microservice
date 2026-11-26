import io
import logging
import os
import random

import qrcode as qr
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


def generate_qrcode(code, version=1, box=10, border=2, color=None, background='white', nologo=False):
    color = tuple([int(rgb * 255) for rgb in [random.random() for _ in range(0, 3)]]) if color is None else color
    qrcode = qr.QRCode(
        version=version,
        box_size=box,
        border=border,
        error_correction=qr.constants.ERROR_CORRECT_H
    )
    qrcode.add_data(code)
    qrcode.make()
    qrcode = qrcode.make_image(fill_color=color, back_color=background).convert('RGB')
    if not nologo:
        logo = Image.open(os.path.join('F:/project/Python/Django/ERPro/static/application/media/erpro.xxhdpi.png')).convert('RGBA')
        rgba = Image.new('RGBA', logo.size, color)
        rgba.paste(logo, mask=logo)
        logo = rgba.convert('RGB')
        logo = ImageOps.expand(logo, border=border * 4, fill=background)
        logo = logo.resize((100, int((float(logo.size[1]) * float(100 / float(logo.size[0]))))), Image.ANTIALIAS)
        qrcode.paste(logo, ((qrcode.size[0] - logo.size[0]) // 2, (qrcode.size[1] - logo.size[1]) // 2))
    return code, qrcode
