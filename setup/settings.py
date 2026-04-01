import json
import os
import re as regex
import sys
from datetime import timedelta
from importlib import import_module
from pathlib import Path

import structlog
from django import get_version
from django.core.serializers.json import DjangoJSONEncoder
from django.db.backends.base.base import RAN_DB_VERSION_CHECK as SkipDatabaseVersionCheck

from core.utils import ShortUUID

try:
    from django.utils.translation import gettext_lazy as _
except:
    _ = lambda string: string

import library.yamlconfig as config
from core import constants

json.JSONEncoder.default = DjangoJSONEncoder.default
PROJECT = {
    'NAME': 'Microservice',
    'VERSION': ('1.0.0', _('Beta Release')),
    'SLOGAN': _('Enterprise ERP For Everyone'),
    'LOGO': '/application/media/microservice',
}
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-n%=mj($&6lx9o&6%#)zjxb02-qze4w8tnd(k4a(!roa3(c%%z-'
SECRET_KEY_FALLBACKS = []
DEBUG = True
ALLOWED_HOSTS = [] if DEBUG else ['*', ]
MANAGE_CLEAR_CONSOLE = True
CORS_ALLOW_ALL_ORIGINS = True
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'

INSTALLED_LIBRARY = [
    'daphne',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.auth',
    'django.contrib.sessions',
    'rest_framework',
    'channels',
    'corsheaders',
]
INSTALLED_MODULE = []
INSTALLED_APPS = INSTALLED_LIBRARY + INSTALLED_MODULE

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'setup.urls'
ASGI_APPLICATION = 'setup.asgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [os.path.join(BASE_DIR, 'templates')],
    'APP_DIRS': False,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.messages.context_processors.messages',
            'core.processors.template',
        ],
        'loaders': [
            'core.loaders.DatabaseLoader',
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ],
    },
}, ]
TEMPLATES_USE_CODEMIRROR = True

DATABASES = {
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, '{0}.sqlite3'.format(PROJECT['NAME'].lower())),
    },
    'postgres': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'django.{0}'.format(PROJECT['NAME'].lower()),
        'USER': PROJECT['NAME'].lower(),
        'PASSWORD': PROJECT['NAME'].lower(),
        'HOST': '127.0.0.1',
        'PORT': 5432,
        'ATOMIC_REQUESTS': True,
    },
}

WHATSAPP = {
    'PORT': 3000,
    'WEBHOOK_URL': 'http://127.0.0.1:8000/whatsapp/webhook/',
    'DOCS': 'http://localhost:3000/docs/',
}

SITE_ID = 1

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

CHANNEL_LAYERS = {
    'memory': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
    'redis': {
        'BACKEND': 'library.channelsredis.pubsub.RedisPubSubChannelLayer',
        'CONFIG': {
            'hosts': ['redis://{user}:{password}@127.0.0.1:6379'.format(user='erpro',password='erpro')],
            'symmetric_encryption_keys': [SECRET_KEY],
        },
    },
}
CHANNEL_MSGPACK = True

CACHES = {
    'dummy': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'cache.{0}.mem'.format(PROJECT['NAME'].lower()),
    },
    'memory': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
    'filebase': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(BASE_DIR, 'data', 'cache'),
    },
    'database': {
        'BACKEND': 'django.core.cache.backends.db.BaseDatabaseCache',
        'LOCATION': u'cache',
    },
    'redis': {
        'BACKEND': 'library.djangoredis.cache.RedisCache',
        'LOCATION': 'redis://{user}:{password}@127.0.0.1:6379'.format(user=PROJECT['NAME'].lower(),
                                                                      password=PROJECT['NAME'].lower()),
        'OPTIONS': {
            'CLIENT_CLASS': 'library.djangoredis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': False,
        },
        'KEY_PREFIX': 'cache',
    },
}
CACHEOPS_ENABLED = True
CACHEOPS_LRU = True
CACHEOPS_REDIS = CACHES['redis']['LOCATION']
CACHEOPS_DEFAULTS = {
    'timeout': 60 * 60,
}
CACHEOPS = {
    'core.*': {'ops': 'all'},
    'migrations.*': None,
    'admin.*': None,
    'library.watson.*': None,
    'contenttypes.*': None,
    'hueymonitor.*': None,
    '*.*': {},
}
CACHEOPS_DEGRADE_ON_FAILURE = True
CACHEOPS_PREFIX = lambda _: 'cacheops'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

HUEYS = {
    'default': 'low',
    'queues': {
        'low': {
            'huey_class': 'huey.PriorityRedisExpireHuey',
            'name': 'low',
            'results': True,
            'store_none': False,
            'immediate': False,
            'utc': True,
            'blocking': True,
            'consumer': {
                'workers': 1,
                'worker_type': 'thread',
                'initial_delay': 0.1,
                'backoff': 1.15,
                'max_delay': 10.0,
                'scheduler_interval': 1,
                'periodic': True,
                'check_worker_health': True,
                'health_check_interval': 1,
            },
        },
        'high': {
            'huey_class': 'huey.PriorityRedisExpireHuey',
            'name': 'high',
            'results': True,
            'store_none': False,
            'immediate': False,
            'utc': True,
            'blocking': True,
            'consumer': {
                'workers': 5,
                'worker_type': 'thread',
                'initial_delay': 0.1,
                'backoff': 1.15,
                'max_delay': 10.0,
                'scheduler_interval': 1,
                'periodic': True,
                'check_worker_health': True,
                'health_check_interval': 1,
            },
        },
    },
}
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            '()': structlog.stdlib.ProcessorFormatter,
            'fmt': '%(message)s',
            'processor': structlog.dev.ConsoleRenderer(force_colors=True, ),
            'foreign_pre_chain': [
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt='iso', utc=False, ),
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.ExceptionPrettyPrinter(),
                structlog.processors.CallsiteParameterAdder({
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }),
            ],
        },
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.processors.JSONRenderer(),
            'foreign_pre_chain': [
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt='iso', utc=False, ),
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.CallsiteParameterAdder({
                    structlog.processors.CallsiteParameter.PATHNAME,
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.MODULE,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.THREAD,
                    structlog.processors.CallsiteParameter.THREAD_NAME,
                    structlog.processors.CallsiteParameter.PROCESS,
                    structlog.processors.CallsiteParameter.PROCESS_NAME,
                }),
            ],
        },
    },
    'filters': {
        'require.debug': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'filters': ['require.debug', ],
            'formatter': 'console',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'filters': ['require.debug', ],
            'formatter': 'json',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'data/log/microservice.json'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 10,
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['default', ],
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['default', ],
    },
}
AUDITLOG_INCLUDE_ALL_MODELS = False

SkipDatabaseVersionCheck.clear()
settings = config.load(base_dir=BASE_DIR, project='microservice', )
from importlib.metadata import version
from core.settings import safesettings

safesettings()
settings.PROJECT.update(
    DJANGO=regex.sub(r'[^\d.]', '', get_version()),
    SERVER='Daphne',
    DAPHNE=regex.sub(r'[^\d.]', '', version('daphne')),
)
if any(item in [
    'uvicorn',
    'runuvicorn',
    'hypercorn',
    'runhypercorn',
] for item in sys.argv):
    setattr(settings, 'CHANNEL_MSGPACK', False)
if any(item in [
    'runserver',
] for item in sys.argv):
    setattr(settings, 'SECURE_SSL_REDIRECT', False)
if not os.path.exists(os.path.dirname(settings.LOGGING['handlers']['file']['filename'])):
    os.makedirs(os.path.dirname(settings.LOGGING['handlers']['file']['filename']))
for module in settings.INSTALLED_MODULE:
    if not os.path.exists(os.path.join(settings.BASE_DIR, module, 'fixtures')):
        os.makedirs(os.path.join(settings.BASE_DIR, module, 'fixtures'))
    if not os.path.exists(os.path.join(settings.BASE_DIR, module, 'locale')):
        os.makedirs(os.path.join(settings.BASE_DIR, module, 'locale'))
for alias, property in settings.DATABASES.items():
    if 'VERSION_CHECK' in property and not property.get('VERSION_CHECK', True):
        SkipDatabaseVersionCheck.add(alias)
settings.DATABASES.update(
    default=settings.DATABASES[getattr(settings, 'DATABASES_DEFAULT', 'sqlite')],
)
settings.CHANNEL_LAYERS.update(
    default=settings.CHANNEL_LAYERS[getattr(settings, 'CHANNEL_DEFAULT', 'memory')],
)
settings.CACHES.update(
    default=settings.CACHES[getattr(settings, 'CACHES_DEFAULT', 'dummy')],
)
setattr(settings, 'CACHEOPS_REDIS', settings.CACHES['redis']['LOCATION'])
for key, queue in settings.HUEYS['queues'].items():
    queue.update(url=settings.CACHES['redis']['LOCATION'], )
if not settings.DEBUG:
    setattr(settings, 'ALLOWED_HOSTS', settings.ALLOWED_HOSTS if len(settings.ALLOWED_HOSTS) > 0 else ['*'], )
    setattr(settings, 'CSRF_TRUSTED_ORIGINS',
            settings.CSRF_TRUSTED_ORIGINS if len(settings.CSRF_TRUSTED_ORIGINS) > 0 else [
                'http://{0}:80'.format(os.environ.get('LOCAL_ADDRESS')),
                'https://{0}:80'.format(os.environ.get('LOCAL_ADDRESS')),
            ], )
    if settings.CSRF_RANDOM:
        setattr(settings, 'CSRF_COOKIE_NAME', f'csrf{ShortUUID().random(length=10)}', )
        setattr(settings, 'CSRF_HEADER_NAME', f'HTTP_X_{settings.CSRF_COOKIE_NAME.upper()}_TOKEN', )
    settings.LOGGING['handlers']['default'].update(formatter='json', )
    settings.LOGGING['loggers']['django.db.backends'].update(
        level='ERROR',
        handlers=['default', 'file', ],
    )
    settings.LOGGING['root'].update(
        level='ERROR',
        handlers=['default', 'file', ],
    )
if any(item in [
    'migrate',
    'makemigrations',
    'showmigrations',
    'collecticon',
    'collectpermission',
    'dumpdata',
    'loaddata',
] for item in sys.argv):
    settings.LOGGING['loggers']['django.db.backends'].update(
        level='INFO',
        handlers=['default', ],
    )

for application in list(filter(lambda applications: os.path.isdir(applications) and os.path.exists(
        os.path.join(applications, 'apps.py')) and not os.path.exists(os.path.join(applications, '.disabled')),
                               os.listdir(settings.BASE_DIR), )):
    def register(application):
        import logging
        logger = logging.getLogger(__name__)
        try:
            module = import_module('%s.%s' % (application, 'apps'))
            if hasattr(module, 'ApplicationConfig'):
                if hasattr(getattr(module, 'ApplicationConfig'), 'dependencies'):
                    for dependencie in list(
                            filter(
                                lambda dependencies: dependencies not in settings.INSTALLED_LIBRARY + settings.INSTALLED_MODULE,
                                getattr(getattr(module, 'ApplicationConfig'), 'dependencies'))):
                        register(dependencie)
                if application not in settings.INSTALLED_LIBRARY + settings.INSTALLED_MODULE:
                    settings.INSTALLED_MODULE.append(application)
                    logger.debug('Auto apps %s.apps append', application)
        except Exception as e:
            logger.info(e)


    register(application)
setattr(settings, 'INSTALLED_APPS', settings.INSTALLED_LIBRARY + settings.INSTALLED_MODULE)
