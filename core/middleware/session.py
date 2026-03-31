import logging
import time

from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings as djangosettings
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from threading import local as _local
except ImportError:
    from _threading_local import _local

_threading_local = _local()
_threading_user = 'user'
_threading_session = 'session'

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object


def _set_threading(request):
    if request.user.is_authenticated:
        setattr(_threading_local, _threading_user, request.user)
    setattr(_threading_local, _threading_session, request.session)


def request():
    if not hasattr(_threading_local, _threading_session):
        setattr(_threading_local, _threading_session, None)
    if not hasattr(_threading_local, _threading_user):
        setattr(_threading_local, _threading_user, None)
    return _threading_local


@property
def is_authenticated():
    return getattr(_threading_local, _threading_user, None) is not None


class SessionThreadLocalMiddleware(MiddlewareMixin):
    def process_request(self, request):
        _set_threading(request)
        req_headers = request.META
        forwarded = req_headers.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            ip_address = forwarded.split(',')[-1].strip()
        else:
            ip_address = req_headers.get('REMOTE_ADDR')
        if request.user and not request.user.is_anonymous and request.user.last_ip_address != ip_address:
            request.user.last_ip_address = ip_address
            request.user.last_activity_date = timezone.now()
            request.user.save()


SESSION_TIMEOUT_KEY = '_session_init_timestamp_'


class SessionTimeoutMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(request, 'session') or request.session.is_empty():
            return
        init_time = request.session.setdefault(SESSION_TIMEOUT_KEY, time.time())
        expire_seconds = getattr(djangosettings, 'SESSION_EXPIRE_SECONDS', djangosettings.SESSION_COOKIE_AGE)
        session_is_expired = time.time() - init_time > expire_seconds
        if session_is_expired:
            request.session.flush()
            redirect_url = getattr(djangosettings, 'SESSION_TIMEOUT_REDIRECT', None)
            next = request.GET.get('next', request.path)
            if next in [redirect_url, ]:
                next = '/home/'
            if redirect_url:
                try:
                    return redirect(f'''{reverse(redirect_url, urlconf=None)}?next={next}''')
                except:
                    return redirect(f'''{redirect_url}?next={next}''')
            else:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(next=request.path)
        expire_since_last_activity = getattr(djangosettings, 'SESSION_EXPIRE_AFTER_LAST_ACTIVITY', False)
        grace_period = getattr(djangosettings, 'SESSION_EXPIRE_AFTER_LAST_ACTIVITY_GRACE_PERIOD', 1)
        if expire_since_last_activity and time.time() - init_time > grace_period:
            request.session[SESSION_TIMEOUT_KEY] = time.time()
