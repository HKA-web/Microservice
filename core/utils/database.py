import logging
import os
import urllib.parse as urlparse

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS as alias, load_backend
from prodict import Prodict

logger = logging.getLogger(__name__)

try:
    from django import VERSION as DJANGO_VERSION
except ImportError:
    DJANGO_VERSION = None
urlparse.uses_netloc.append('postgres')
urlparse.uses_netloc.append('postgresql')
urlparse.uses_netloc.append('pgsql')
urlparse.uses_netloc.append('postgis')
urlparse.uses_netloc.append('mysql')
urlparse.uses_netloc.append('mysqlgis')
urlparse.uses_netloc.append('mysqlconnector')
urlparse.uses_netloc.append('mssql')
urlparse.uses_netloc.append('mssqlms')
urlparse.uses_netloc.append('spatialite')
urlparse.uses_netloc.append('sqlite')
urlparse.uses_netloc.append('oracle')
urlparse.uses_netloc.append('oraclegis')
urlparse.uses_netloc.append('redshift')
urlparse.uses_netloc.append('cockroach')
urlparse.uses_netloc.append('timescale')
urlparse.uses_netloc.append('timescalegis')
ENV = 'DATABASE_URL'
SCHEMES = dict(
    postgis='django.contrib.gis.db.backends.postgis',
    mysql='django.db.backends.mysql',
    mysqlgis='django.contrib.gis.db.backends.mysql',
    mysqlconnector='mysql.connector.django',
    mssql='library.pyodbc',
    mssqlms='mssql',
    spatialite='django.contrib.gis.db.backends.spatialite',
    sqlite='django.db.backends.sqlite3',
    oracle='django.db.backends.oracle',
    oraclegis='django.contrib.gis.db.backends.oracle',
    redshift='django_redshift_backend',
    cockroach='django_cockroachdb',
    timescale='timescale.db.backends.postgresql',
    timescalegis='timescale.db.backends.postgis',
)
if DJANGO_VERSION and DJANGO_VERSION < (2, 0):
    SCHEMES['postgres'] = 'django.db.backends.postgresql_psycopg2'
    SCHEMES['postgresql'] = 'django.db.backends.postgresql_psycopg2'
    SCHEMES['pgsql'] = 'django.db.backends.postgresql_psycopg2'
else:
    SCHEMES['postgres'] = 'django.db.backends.postgresql'
    SCHEMES['postgresql'] = 'django.db.backends.postgresql'
    SCHEMES['pgsql'] = 'django.db.backends.postgresql'


def config(env=ENV, default=None, engine=None, conn_max_age=0, ssl_require=False):
    string = os.environ.get(env, default)
    if string:
        return parse(string, engine, conn_max_age, ssl_require)
    return {}


def parse(url, engine=None, conn_max_age=0, ssl_require=False):
    if url == 'sqlite://:memory:':
        return dict(
            ENGINE=SCHEMES['sqlite'],
            NAME=':memory:'
        )
    configure = {}
    url = urlparse.urlparse(url)
    path = url.path[1:]
    if '?' in path and not url.query:
        path, query = path.split('?', 2)
    else:
        path, query = path, url.query
    query = urlparse.parse_qs(query)
    if url.scheme == 'sqlite' and path == '':
        path = ':memory:'
    hostname = url.hostname or ''
    if '%2f' in hostname.lower():
        hostname = url.netloc
        if '@' in hostname:
            hostname = hostname.rsplit('@', 1)[1]
        if ':' in hostname:
            hostname = hostname.split(':', 1)[0]
        hostname = hostname.replace('%2f', '/').replace('%2F', '/')
    engine = SCHEMES[url.scheme] if engine is None else engine
    port = (str(url.port) if url.port and engine in [SCHEMES['oracle'], SCHEMES['mssql'], SCHEMES['mssqlms']] else url.port)
    configure.update(dict(
        NAME=urlparse.unquote(path or ''),
        USER=urlparse.unquote(url.username or ''),
        PASSWORD=urlparse.unquote(url.password or ''),
        HOST=hostname,
        PORT=port or '',
        CONN_MAX_AGE=conn_max_age,
    ))
    options = {}
    for key, values in query.items():
        if url.scheme == 'mysql' and key == 'ssl-ca':
            options['ssl'] = dict(ca=values[-1])
            continue
        options[key] = values[-1]
    if ssl_require:
        options['sslmode'] = 'require'
    if 'currentSchema' in options and engine in (
        'django.contrib.gis.db.backends.postgis',
        'django.db.backends.postgresql_psycopg2',
        'django.db.backends.postgresql',
        'django_redshift_backend',
        'timescale.db.backends.postgresql',
        'timescale.db.backends.postgis',
    ):
        options['options'] = '-c search_path={0}'.format(options.pop('currentSchema'))
    if options:
        configure['OPTIONS'] = options
    if engine:
        configure['ENGINE'] = engine
    return configure


def create(alias=alias):
    database = connections.databases[alias]
    database.setdefault('ATOMIC_REQUESTS', False)
    database.setdefault('AUTOCOMMIT', True)
    database.setdefault('ENGINE', 'django.db.backends.dummy')
    database.setdefault('CONN_MAX_AGE', 0)
    database.setdefault('CONN_HEALTH_CHECKS', False)
    database.setdefault('OPTIONS', {})
    database.setdefault('TIME_ZONE', None)
    for setting in ['NAME', 'USER', 'PASSWORD', 'HOST', 'PORT']:
        database.setdefault(setting, '')
    connections.create_connection(alias)
    from django.db.backends.base.base import RAN_DB_VERSION_CHECK as SkipDatabaseVersionCheck
    SkipDatabaseVersionCheck.add(alias)
    backend = load_backend(database['ENGINE'])
    return backend.DatabaseWrapper(database, alias)


def fetchall(connection, query, clause=None, autoclose=True):
    import json
    cursor = connection.cursor()
    cursor.execute(f'''{query}''', clause)
    result = []
    fetchall = cursor.fetchall()
    if fetchall is None:
        return fetchall
    for value in fetchall:
        temporary = {}
        for (index, column) in enumerate(value):
            try:
                column = json.loads(column)
            except:
                pass
            temporary[cursor.description[index][0]] = column
        result.append(Prodict.from_dict(temporary))
    if autoclose:
        connection.close()
    return result


def fetchone(connection, query, clause=None, autoclose=True):
    import json
    cursor = connection.cursor()
    cursor.execute(f'''{query}''', clause)
    result = {}
    fetchone = cursor.fetchone()
    if fetchone is None:
        return fetchone
    for (index, column) in enumerate(fetchone):
        try:
            column = json.loads(column)
        except:
            pass
        result[cursor.description[index][0]] = column
    result = Prodict.from_dict(result)
    if autoclose:
        connection.close()
    return result


def update(connection, query, value=None, autoclose=True):
    cursor = connection.cursor()
    cursor.execute(f'''{query}''', value)
    result = cursor.rowcount
    if autoclose:
        connection.close()
    return result


def execute(connection, query, value=None, autoclose=True):
    return update(connection, query, value, autoclose)


def executemany(connection, query, value=None, autoclose=True):
    return execute(connection, query, value, autoclose)


def delete(connection, query, value=None, autoclose=True):
    return update(connection, query, value, autoclose)
