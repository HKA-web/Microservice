import io
import logging
import os

from django.db import migrations
from django.conf import settings as djangosettings
logger = logging.getLogger(__name__)


def code(apps, schema_editor):
    alias = schema_editor.connection.alias
    for module in djangosettings.INSTALLED_MODULE:
        for dirpath, subdirs, filenames in os.walk(os.path.realpath(os.path.join(djangosettings.BASE_DIR, module, 'migrations'))):
            for file in [file for file in filenames if file.endswith('.sql') and not file.startswith('.')]:
                input = os.path.join(dirpath, file).replace('\\', '/')
                print('Sql', input)
                with io.open(input, mode='r', ) as sql:
                    sql = sql.read()
                    print('Sql', sql)
    from core.sql.models import DjangoMigrations
    DjangoMigrations.objects.using(alias).filter(
        app='sql',
        name=os.path.splitext(os.path.basename(__file__))[0],
    ).delete()


def reverse_code(apps, schema_editor):
    alias = schema_editor.connection.alias
    sqls = []
    sqls.append('CREATE SCHEMA IF NOT EXISTS demo')
    sqls.append('CREATE SCHEMA IF NOT EXISTS coba_coba')
    print('\n')
    for sql in sqls:
        print(f'Execute {sql}')
    for module in djangosettings.INSTALLED_MODULE:
        for dirpath, subdirs, filenames in os.walk(os.path.realpath(os.path.join(djangosettings.BASE_DIR, module, 'migrations'))):
            for file in [file for file in filenames if file.endswith('.sql') and not file.startswith('.')]:
                input = os.path.join(dirpath, file).replace('\\', '/')
                print('Sql', input)
    from core.sql.models import DjangoMigrations
    DjangoMigrations.objects.using(alias).filter(
        app='sql',
        name=os.path.splitext(os.path.basename(__file__))[0],
    ).delete()


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunPython(
            code=code,
            reverse_code=reverse_code,
        )
    ]
