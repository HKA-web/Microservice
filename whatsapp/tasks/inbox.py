import json
import logging
import os
import platform
import re as regex
from collections import namedtuple
from datetime import datetime

import psutil
from django.conf import settings as djangosettings
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import library.djangohuey as huey
from core.utils import ShortUUID
from whatsapp.apps import ApplicationConfig
from whatsapp.models import Inbox, Outbox, Command, CommandActive

logger = logging.getLogger(__name__)


def prepare(inbox: Inbox):
    """
    Mencocokkan pesan masuk (inbox) dengan Command yang tersedia di tabel whatsapp.command,
    atau melanjutkan alur percakapan bertingkat dari CommandActive sebelumnya.
    """
    command_active = None

    def check(cmd_text: str):
        if not cmd_text:
            return None
        # 1. Cari exact match (sesi yang sama atau global session)
        searchs = Command.objects.using('WHATSAPP').filter(
            Q(session_id=inbox.session_id) | Q(session_id__isnull=True) | Q(session_id=''),
            command__iexact=cmd_text,
            enable=True,
        )
        # 2. Cari dengan format slash (contoh: 'cek poin' -> 'cek/poin')
        if not searchs.exists():
            searchs = Command.objects.using('WHATSAPP').filter(
                Q(session_id=inbox.session_id) | Q(session_id__isnull=True) | Q(session_id=''),
                command__iexact='/'.join(cmd_text.split()),
                enable=True,
            )
        if searchs.exists():
            return searchs
        
        # 3. Rekursi dengan longest prefix (contoh: 'cek poin 12345' -> coba 'cek poin')
        parts = cmd_text.split()
        if len(parts) > 1:
            next_prefix = ' '.join(parts[:-1])
            return check(next_prefix.strip())
        return None

    cmd_raw = inbox.command.strip() if inbox.command else ''
    clean_words = ' '.join(regex.split(r'\W+', cmd_raw)) if cmd_raw else ''
    commands = check(clean_words) if clean_words else None

    if commands and commands.exists():
        for cmd in commands:
            # Ekstraksi parameter positional jika ada sisa kata setelah nama command
            cmd_key = cmd.command.strip().lower()
            if cmd_raw.lower() not in (cmd_key,):
                cmd_len = len(cmd.command.strip())
                trailing_params = cmd_raw[cmd_len:].split()
                formatted_params = list(trailing_params)
                req_params = cmd.required_parameter or []
                for idx, req_item in enumerate(req_params):
                    if idx < len(formatted_params):
                        formatted_params[idx] = f"{req_item}={formatted_params[idx]}"
                inbox.message = f"{cmd_raw[:cmd_len].strip().lower()}\n" + '\n'.join(formatted_params)
                inbox.save(using='WHATSAPP', update_fields=['message'])

            command_active = CommandActive.objects.using('WHATSAPP').create(
                command=cmd,
                command_by=inbox.inbox_by,
                parameter=inbox.parameter,
                enable=True,
            )
            break
    else:
        # Jika bukan command langsung, periksa apakah user memiliki sesi aktif sebelumnya di CommandActive
        actives = CommandActive.objects.using('WHATSAPP').filter(
            command_by=inbox.inbox_by,
            enable=True,
        )
        if inbox.session_id:
            actives = actives.filter(Q(command__session_id=inbox.session_id) | Q(command__session_id__isnull=True))

        for active in actives:
            chained_name = f"{active.command.command}/{cmd_raw}".strip()
            chained_clean = ' '.join(regex.split(r'\W+', chained_name))
            commands = check(chained_clean)
            if commands and commands.exists():
                for cmd in commands:
                    command_active = CommandActive.objects.using('WHATSAPP').create(
                        command=cmd,
                        command_by=inbox.inbox_by,
                        parameter=inbox.parameter,
                        enable=True,
                    )
                    break
            if command_active:
                break

    # Pengecekan parameter wajib (required_parameter)
    if command_active:
        target_cmd = command_active.command.mirror if command_active.command.mirror else command_active.command
        req_params = target_cmd.required_parameter or []
        chk_param = target_cmd.check_parameter

        if chk_param and req_params:
            missing = [p for p in req_params if p not in (command_active.parameter or {})]
            if missing:
                missing_str = '\n'.join(missing)
                Outbox.objects.using('WHATSAPP').create(
                    message=f"Parameter \n{missing_str} \nIs Required",
                    message_type='conversation',
                    outbox_for=inbox.inbox_by,
                    session_id=inbox.session_id,
                    properties=dict(command=target_cmd.pk, inbox=inbox.inbox_id, reply_to=inbox.inbox_id),
                    data=dict(reply_to=inbox.inbox_id, quoted=inbox.data),
                )
                return None

    return command_active


def _mark_processed(inbox: Inbox):
    inbox.is_processed = True
    try:
        if inbox.pk and not inbox._state.adding:
            inbox.save(using='WHATSAPP', update_fields=['is_processed'])
        else:
            inbox.save(using='WHATSAPP')
    except Exception as save_err:
        logger.debug(f"Could not update is_processed on inbox: {save_err}")


def process_inbox_sync(inbox: Inbox):
    """
    Eksekusi logika pesan masuk secara sinkron (direct execution).
    """
    if not inbox or inbox.is_processed:
        return

    cmd_text = inbox.command or ''
    cmd_normalized = '/'.join(cmd_text.strip().lower().split()) if cmd_text else ''

    # -------------------------------------------------------------
    # 1. Built-in Command: ping
    # -------------------------------------------------------------
    if cmd_normalized in ('ping',):
        ref = ShortUUID().random(length=5)
        reply = f"Pong, saldo saya tidak cukup untuk melayani ping anda.... 😒\n\n__ref:{ref}__"
        Outbox.objects.using('WHATSAPP').create(
            message=reply,
            message_type='conversation',
            outbox_for=inbox.inbox_by,
            session_id=inbox.session_id,
            properties=dict(inbox=inbox.inbox_id, reply_to=inbox.inbox_id),
            data=dict(reply_to=inbox.inbox_id, quoted=inbox.data),
        )
        _mark_processed(inbox)
        logger.info(f"🏓 [BUILTIN COMMAND] 'ping' dijawab untuk {inbox.inbox_by}")
        return

    # -------------------------------------------------------------
    # 2. Built-in Command: whatsapp/info atau info
    # -------------------------------------------------------------
    if cmd_normalized in ('whatsapp/info', 'info'):
        try:
            cpu_pct = psutil.cpu_percent(interval=0.3)
            vmem = psutil.virtual_memory()
            ram_used = round(vmem.used / (1024 ** 3), 2)
            ram_total = round(vmem.total / (1024 ** 3), 2)
            ram_pct = vmem.percent
            disk = psutil.disk_usage('/')
            disk_free = round(disk.free / (1024 ** 3), 2)
            disk_total = round(disk.total / (1024 ** 3), 2)

            info_msg = (
                f"📊 *Informasi Sistem Server:*\n\n"
                f"• *OS:* {platform.system()} {platform.release()}\n"
                f"• *CPU Usage:* {cpu_pct}%\n"
                f"• *RAM:* {ram_used} GB / {ram_total} GB ({ram_pct}%)\n"
                f"• *Disk:* {disk_free} GB Free / {disk_total} GB\n"
                f"• *Waktu Server:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            Outbox.objects.using('WHATSAPP').create(
                message=info_msg,
                message_type='conversation',
                outbox_for=inbox.inbox_by,
                session_id=inbox.session_id,
                properties=dict(inbox=inbox.inbox_id, reply_to=inbox.inbox_id),
                data=dict(reply_to=inbox.inbox_id, quoted=inbox.data),
            )
            _mark_processed(inbox)
            logger.info(f"ℹ️ [BUILTIN COMMAND] 'whatsapp/info' dijawab untuk {inbox.inbox_by}")
            return
        except Exception as err:
            logger.error(f"Error executing whatsapp/info: {err}")

    # -------------------------------------------------------------
    # 3. Dynamic Command Execution via Command & CommandActive
    # -------------------------------------------------------------
    command_active = prepare(inbox)
    if command_active:
        target_cmd = command_active.command.mirror if command_active.command.mirror else command_active.command
        processes = target_cmd.process or []

        for proc in processes:
            logger.info(f"⚡ [EXEC COMMAND] {target_cmd.command} (Type: {target_cmd.command_type})")

            # A. Tipe TXT (Template Formatting)
            if target_cmd.command_type in (Command.Type.TXT, 'txt'):
                try:
                    formatted_msg = proc.format(
                        environment=namedtuple('Environment', os.environ.keys(), rename=True)(*os.environ.values()),
                        setting=djangosettings,
                        now=timezone.now(),
                        inbox=inbox,
                        command_active=command_active,
                    )
                except Exception:
                    formatted_msg = str(proc)

                Outbox.objects.using('WHATSAPP').create(
                    message=formatted_msg,
                    message_type='conversation',
                    outbox_for=inbox.inbox_by,
                    session_id=inbox.session_id,
                    properties=dict(command=target_cmd.pk, inbox=inbox.inbox_id, reply_to=inbox.inbox_id),
                    data=dict(reply_to=inbox.inbox_id, quoted=inbox.data),
                )

            # B. Tipe SQL (Django Template Query Execution)
            elif target_cmd.command_type in (Command.Type.SQL, 'sql'):
                try:
                    from django.template import Context, Template
                    from django.db import connections
                    rendered_sql = Template(str(proc)).render(
                        Context(dict(inbox=inbox, command_active=command_active))
                    )
                    with connections['WHATSAPP'].cursor() as cursor:
                        cursor.execute(rendered_sql)
                    logger.info(f"✅ [SQL EXEC SUCCESS] Query: {rendered_sql[:50]}...")
                except Exception as sql_err:
                    logger.error(f"❌ [SQL EXEC ERROR] {sql_err}", exc_info=True)

            # C. Tipe PY (Dynamic Python Script Execution)
            elif target_cmd.command_type in (Command.Type.PY, 'py'):
                try:
                    result_scope = dict()
                    proc_indented = '\n\t'.join(str(proc).strip().splitlines())
                    exec_code = f"def function():\n\t{proc_indented}".strip()
                    exec(exec_code, dict(
                        inbox=inbox,
                        command_active=command_active,
                    ), result_scope)
                    fn = result_scope[list(result_scope)[-1]]
                    fn()
                    logger.info(f"✅ [PY EXEC SUCCESS] Script executed for {target_cmd.command}")
                except Exception as py_err:
                    logger.error(f"❌ [PY EXEC ERROR] {py_err}", exc_info=True)

        # Jika is_finish == True, bersihkan command active
        if target_cmd.is_finish:
            try:
                command_active.delete(using='WHATSAPP', soft=False)
            except Exception as del_err:
                logger.warning(f"Error deleting CommandActive: {del_err}")

    _mark_processed(inbox)


@huey.db_task(name='Process Inbox Task', queue=ApplicationConfig.name)
def process(inbox: Inbox):
    """
    Task worker asynchronous untuk memproses Inbox via antrean Huey.
    """
    process_inbox_sync(inbox)
