import json
import logging
import os

import yaml
from django.conf import settings as djangosettings
from django.core.management.base import BaseCommand
from django.db import connection

from core.models import Icon
from core.utils import StringCase

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Management command to collect icon library'

    def handle(self, *args, **kwargs):
        self.stdout.write(f'''{os.linesep}{self.help}{os.linesep}{os.linesep}''')
        icons = yaml.load(open(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, f'vendor/fontawesome/metadata/icons.yml'), 'r'), Loader=yaml.Loader)
        families = yaml.load(open(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, f'vendor/fontawesome/metadata/icons.yml'), 'r'), Loader=yaml.Loader)
        categories = yaml.load(open(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, f'vendor/fontawesome/metadata/categories.yml'), 'r'), Loader=yaml.Loader)
        connection.cursor().execute('TRUNCATE TABLE {0}'.format(Icon._meta.db_table))
        for icon, value in icons.items():
            value.update(families[icon])
            icon = Icon.objects.create(
                icon_name=value['label'],
                icon=icon,
                library='fontawesome',
                read_only=True,
                enable=True,
                properties=value,
            )
            self.stdout.write(f'''Icon {icon.icon_name} created''')
        for categorie, value in categories.items():
            for icon in value['icons']:
                for icon in Icon.objects.filter(icon=icon, library='fontawesome', ):
                    properties = icon.properties
                    properties.update(dict(categorie=dict(
                        id=categorie,
                        name=value['label'],
                    ), ))
                    icon.properties = properties
                    icon.save()
        codepoints = json.load(open(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, 'vendor/materialicons/metadata/codepoints.json'), 'r'))
        versions = json.load(open(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, 'vendor/materialicons/metadata/versions.json'), 'r'))
        for icon, version in versions.items():
            icon, created = Icon.objects.get_or_create(
                icon=StringCase.spinalcase(icon),
                library='materialicons',
                defaults=dict(
                    icon_name=StringCase.titlecase(icon),
                    icon=StringCase.spinalcase(icon),
                    library='materialicons',
                    read_only=True,
                    enable=True,
                    properties=dict(
                        label=StringCase.titlecase(icon),
                        styles=['outlined', 'round', 'sharp', 'two-tone', ],
                        changes=[version, ],
                        unicode=str(codepoints.get(icon)),
                        categorie=dict(
                            id='materialicons',
                            name='Material Icons',
                        ),
                    ),
                )
            )
            self.stdout.write(f'''Icon {icon.icon_name} created''')
        weathericons = yaml.load(open(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, 'vendor/weathericons/values/weathericons.yaml'), 'r'), Loader=yaml.Loader)
        utility = yaml.load(open(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, 'vendor/weathericons/values/utility.yaml'), 'r'), Loader=yaml.Loader)
        for category, icons in weathericons.items():
            for icon in icons:
                icon, created = Icon.objects.get_or_create(
                    icon=StringCase.spinalcase(icon),
                    library='weathericons',
                    defaults=dict(
                        icon_name=StringCase.titlecase(icon[3:]),
                        icon=StringCase.spinalcase(icon),
                        library='weathericons',
                        read_only=True,
                        enable=True,
                        properties=dict(
                            label=StringCase.titlecase(icon),
                            changes=['2.0.12', ],
                            categorie=dict(
                                id=StringCase.spinalcase(category).lower(),
                                name=category,
                            ),
                        ),
                    )
                )
                icon.properties.update(
                    utilities=utility,
                )
                for _, utilities in utility.items():
                    if _ in ['Rotate', 'Flip', 'Fixed Width', ]:
                        styles = icon.properties.get('styles', [])
                        styles = styles + utilities
                        icon.properties.update(
                            styles=styles,
                        )
                icon.save()
                self.stdout.write(f'''Icon {icon.icon_name} created''')
        flags = [names for names in [files for (path, directories, files) in os.walk(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, f'vendor/famfamfam/src/flags/'))][0] if names.endswith('.gif')]
        for icon in flags:
            name, extension = os.path.splitext(icon)
            icon, created = Icon.objects.get_or_create(
                icon_name=name,
                library='famfamfam',
                defaults=dict(
                    icon_name=name,
                    icon=name,
                    library='famfamfam',
                    read_only=True,
                    enable=True,
                    properties=dict(
                        label=name,
                        file=icon,
                        extension=extension,
                        styles=['flags', ],
                        changes=['00', ],
                        categorie=dict(
                            id='flags',
                            name='Flags',
                        ),
                    ),
                )
            )
            if not created:
                properties = dict(
                    label=name,
                    file=icon,
                    extension=extension,
                    styles=['flags', ],
                    changes=['000', ],
                    categorie=dict(
                        id='flags',
                        name='Flags',
                    ),
                )
                if icon.properties['file'] != properties['file']:
                    properties.update(file=f'''{icon.properties['file']}, {properties['file']}''')
                if icon.properties['extension'] != properties['extension']:
                    properties.update(extension=f'''{icon.properties['extension']}, {properties['extension']}''')
                properties.update(styles=icon.properties['styles'] + properties['styles'])
                properties.update(changes=icon.properties['changes'] + properties['changes'])
                properties.update(categorie=dict(
                    id=f'''{icon.properties['categorie']['id']}, {properties['categorie']['id']}''',
                    name=f'''{icon.properties['categorie']['name']}, {properties['categorie']['name']}''',
                ))
                icon.properties.update(properties)
                icon.save()
            self.stdout.write(f'''Icon {icon.icon_name} created''')
        mini = [names for names in [names for (path, directory, names) in os.walk(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, f'vendor/famfamfam/src/mini/'))][0] if names.endswith('.gif')]
        for icon in mini:
            name, extension = os.path.splitext(icon)
            icon, created = Icon.objects.get_or_create(
                icon=name,
                library='famfamfam',
                defaults=dict(
                    icon_name=StringCase.titlecase(name),
                    icon=name,
                    library='famfamfam',
                    read_only=True,
                    enable=True,
                    properties=dict(
                        label=StringCase.titlecase(name),
                        file=icon,
                        extension=extension,
                        styles=['mini', ],
                        changes=['00', ],
                        categorie=dict(
                            id='mini',
                            name='Mini',
                        ),
                    ),
                )
            )
            if not created:
                properties = dict(
                    label=StringCase.titlecase(name),
                    file=icon,
                    extension=extension,
                    styles=['mini', ],
                    changes=['000', ],
                    categorie=dict(
                        id='mini',
                        name='Mini',
                    ),
                )
                if icon.properties['file'] != properties['file']:
                    properties.update(file=f'''{icon.properties['file']}, {properties['file']}''')
                if icon.properties['extension'] != properties['extension']:
                    properties.update(extension=f'''{icon.properties['extension']}, {properties['extension']}''')
                properties.update(styles=icon.properties['styles'] + properties['styles'])
                properties.update(changes=icon.properties['changes'] + properties['changes'])
                properties.update(categorie=dict(
                    id=f'''{icon.properties['categorie']['id']}, {properties['categorie']['id']}''',
                    name=f'''{icon.properties['categorie']['name']}, {properties['categorie']['name']}''',
                ))
                icon.properties.update(properties)
                icon.save()
            self.stdout.write(f'''Icon {icon.icon_name} created''')
        silk = [names for names in [names for (path, directory, names) in os.walk(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, f'vendor/famfamfam/src/silk/'))][0] if names.endswith('.png')]
        for icon in silk:
            name, extension = os.path.splitext(icon)
            icon, created = Icon.objects.get_or_create(
                icon=name,
                library='famfamfam',
                defaults=dict(
                    icon_name=StringCase.titlecase(name),
                    icon=name,
                    library='famfamfam',
                    read_only=True,
                    enable=True,
                    properties=dict(
                        label=StringCase.titlecase(name),
                        file=icon,
                        extension=extension,
                        styles=['silk', ],
                        changes=['00', ],
                        categorie=dict(
                            id='silk',
                            name='Silk',
                        ),
                    ),
                )
            )
            if not created:
                properties = dict(
                    label=StringCase.titlecase(name),
                    file=icon,
                    extension=extension,
                    styles=['silk', ],
                    changes=['000', ],
                    categorie=dict(
                        id='silk',
                        name='Silk',
                    ),
                )
                if icon.properties['file'] != properties['file']:
                    properties.update(file=f'''{icon.properties['file']}, {properties['file']}''')
                if icon.properties['extension'] != properties['extension']:
                    properties.update(extension=f'''{icon.properties['extension']}, {properties['extension']}''')
                properties.update(styles=icon.properties['styles'] + properties['styles'])
                properties.update(changes=icon.properties['changes'] + properties['changes'])
                properties.update(categorie=dict(
                    id=f'''{icon.properties['categorie']['id']}, {properties['categorie']['id']}''',
                    name=f'''{icon.properties['categorie']['name']}, {properties['categorie']['name']}''',
                ))
                icon.properties.update(properties)
                icon.save()
            self.stdout.write(f'''Icon {icon.icon_name} created''')
        vendor = [names for names in [names for (path, directory, names) in os.walk(os.path.join(djangosettings.STATICFILES_DIRS[0] if djangosettings.DEBUG else djangosettings.STATIC_ROOT, f'vendor/famfamfam/src/vendor/'))][0] if names.endswith('.png')]
        for icon in vendor:
            name, extension = os.path.splitext(icon)
            icon, created = Icon.objects.get_or_create(
                icon=name,
                library='famfamfam',
                defaults=dict(
                    icon_name=StringCase.titlecase(name),
                    icon=name,
                    library='famfamfam',
                    read_only=True,
                    enable=True,
                    properties=dict(
                        label=StringCase.titlecase(name),
                        file=icon,
                        extension=extension,
                        styles=['vendor-16x16', ],
                        changes=['00', ],
                        categorie=dict(
                            id='vendor',
                            name='Vendor',
                        ),
                    ),
                )
            )
            if not created:
                properties = dict(
                    label=StringCase.titlecase(name),
                    file=icon,
                    extension=extension,
                    styles=['vendor-16x16', ],
                    changes=['000', ],
                    categorie=dict(
                        id='vendor',
                        name='Vendor',
                    ),
                )
                if icon.properties['file'] != properties['file']:
                    properties.update(file=f'''{icon.properties['file']}, {properties['file']}''')
                if icon.properties['extension'] != properties['extension']:
                    properties.update(extension=f'''{icon.properties['extension']}, {properties['extension']}''')
                properties.update(styles=icon.properties['styles'] + properties['styles'])
                properties.update(changes=icon.properties['changes'] + properties['changes'])
                properties.update(categorie=dict(
                    id=f'''{icon.properties['categorie']['id']}, {properties['categorie']['id']}''',
                    name=f'''{icon.properties['categorie']['name']}, {properties['categorie']['name']}''',
                ))
                icon.properties.update(properties)
                icon.save()
            self.stdout.write(f'''Icon {icon.icon_name} created''')
        self.stdout.write(f'''Total {Icon.objects.count()} icons collected''')
