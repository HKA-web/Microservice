import io
import logging
import os
from random import randint

import minify_html
from django.apps import apps
from django.db import router
from django.db.models import signals
from django.conf import settings as djangosettings
from core.utils import StringCase

__all__ = []

from django.template.utils import get_app_template_dirs

logger = logging.getLogger(__name__)


def create_site(sender, **kwargs):
    try:
        Site = apps.get_model('sites', 'Site')
        if not router.allow_migrate_model(kwargs['using'], Site):
            return
        site, created = Site.objects.using(kwargs['using']).get_or_create(
            pk=getattr(djangosettings, 'SITE_ID'),
            defaults=dict(
                id=getattr(djangosettings, 'SITE_ID'),
                name=getattr(djangosettings, 'SITE_NAME', djangosettings.PROJECT['NAME']),
                domain=getattr(djangosettings, 'SITE_DOMAIN', '127.0.0.1'),
            ),
        )
        if not created and site.domain in ['example.com']:
            logger.info('Site %s created', site.pk)
            site.name = getattr(djangosettings, 'SITE_NAME', djangosettings.PROJECT['NAME'])
            site.domain = getattr(djangosettings, 'SITE_DOMAIN', '127.0.0.1')
            site.save()
    except Exception as e:
        logger.warning(str(e))
        return


signals.post_migrate.connect(
    create_site,
    sender=apps.get_app_config('sites'),
    dispatch_uid='core.management.create_site',
)


def create_company(sender, **kwargs):
    try:
        Province = apps.get_model('core', 'Province')
        City = apps.get_model('core', 'City')
        District = apps.get_model('core', 'District')
        Village = apps.get_model('core', 'Village')
        Company = apps.get_model('core', 'Company')
        if not router.allow_migrate_model(kwargs['using'], Province) or not router.allow_migrate_model(kwargs['using'], City) or not router.allow_migrate_model(kwargs['using'], District) or not router.allow_migrate_model(kwargs['using'], Village) or not router.allow_migrate_model(kwargs['using'], Company):
            return
        province, created = Province.objects.using(kwargs['using']).get_or_create(
            province_id=djangosettings.PROJECT.get('NAME'),
            defaults=dict(
                province_id=djangosettings.PROJECT.get('NAME'),
                province_name=djangosettings.PROJECT.get('NAME'),
            ),
        )
        if created:
            logger.info('Province %s created', province)
        city, created = City.objects.using(kwargs['using']).get_or_create(
            city_id=djangosettings.PROJECT.get('NAME'),
            defaults=dict(
                city_id=djangosettings.PROJECT.get('NAME'),
                city_name=djangosettings.PROJECT.get('NAME'),
                province=province,
            ),
        )
        if created:
            logger.info('City %s created', city)
        district, created = District.objects.using(kwargs['using']).get_or_create(
            district_id=djangosettings.PROJECT.get('NAME'),
            defaults=dict(
                district_id=djangosettings.PROJECT.get('NAME'),
                district_name=djangosettings.PROJECT.get('NAME'),
                city=city,
            ),
        )
        if created:
            logger.info('District %s created', district)
        village, created = Village.objects.using(kwargs['using']).get_or_create(
            village_id=djangosettings.PROJECT.get('NAME'),
            defaults=dict(
                village_id=djangosettings.PROJECT.get('NAME'),
                village_name=djangosettings.PROJECT.get('NAME'),
                district=district,
            ),
        )
        if created:
            logger.info('Village %s created', village)
        company, created = Company.objects.using(kwargs['using']).get_or_create(
            company_id=djangosettings.PROJECT.get('NAME'),
            defaults=dict(
                name=djangosettings.PROJECT.get('NAME'),
                province=province,
                city=city,
                district=district,
                village=village,
                website=f'''www.{djangosettings.PROJECT.get('NAME')}.local'''.lower(),
            ),
        )
        if created:
            logger.info('Company %s created', company)
    except Exception as e:
        logger.warning(str(e))
        return


signals.post_migrate.connect(
    create_company,
    sender=apps.get_app_config('core'),
    dispatch_uid='core.management.create_company',
)


def create_screen_saver(sender, **kwargs):
    try:
        ScreenSaver = apps.get_model('core', 'ScreenSaver')
        if not router.allow_migrate_model(kwargs['using'], ScreenSaver):
            return
        for templatedir in [
            template for template in [
                str(dir) for dir in get_app_template_dirs('templates') if os.path.isdir(dir)
            ] if any(module in template for module in ['core'])
        ]:
            for dirpath, subdirs, filenames in os.walk(os.path.join(templatedir, 'core', 'screensaver', 'data')):
                for file in [file for file in filenames if file.endswith('html') and not file.startswith('.')]:
                    path = os.path.join(dirpath, file)
                    with io.open(path, encoding='utf-8') as content:
                        content = content.read()
                        content = minify_html.minify(content, minify_css=True, minify_js=True, keep_comments=False, )
                        screen_saver, created = ScreenSaver.objects.using(kwargs['using']).get_or_create(
                            screen_saver_name=StringCase.titlecase(file.replace('.html', '')),
                            defaults=dict(
                                screen_saver_name=StringCase.titlecase(file.replace('.html', '')),
                                content=content,
                                default=False,
                                enable=True,
                            ),
                        )
                        if created:
                            logger.info('Screen saver %s created', screen_saver.screen_saver_name)
                        else:
                            screen_saver.content = content
                            screen_saver.save(update_fields=['content', ])
        screen_savers = ScreenSaver.objects.filter(enable=True, default=True, )
        for screen_saver in screen_savers:
            screen_saver.default = False
            screen_saver.save(update_fields=['default', ])
        if len(screen_savers) > 0:
            screen_saver = screen_savers[randint(0, len(screen_savers) - 1)]
            screen_saver.default = True
            screen_saver.save(update_fields=['default', ])
            logger.info('Screen saver %s as default', screen_saver.screen_saver_name)
    except Exception as e:
        logger.warning(str(e))
        return


signals.post_migrate.connect(
    create_screen_saver,
    sender=apps.get_app_config('core'),
    dispatch_uid='core.management.create_screen_saver',
)
