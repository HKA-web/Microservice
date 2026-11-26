import logging
import os
import subprocess
from pathlib import Path

import library.djangohuey as huey

logger = logging.getLogger(__name__)


@huey.db_task(name='Command Line', )
def process(command: str = None, ):
    cwd = Path(__file__).resolve().parent.parent.parent
    logger.info(str(command))
    process = subprocess.Popen(
        command,
        env=os.environ,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=cwd,
        encoding='cp850',
        shell=True,
    )
    for outline in iter(process.stdout.readline, ''):
        logger.info(str(outline))
    for outline in iter(process.stderr.readline, ''):
        logger.info(str(outline))
