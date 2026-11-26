import logging
import sys

from django.shortcuts import render

logger = logging.getLogger(__name__)


def bad_request(request, exception):
    return render(request, 'error/400.html', {})


def permission_denied(request, exception):
    return render(request, 'error/403.html', {})


def page_not_found(request, exception):
    return render(request, 'error/404.html', {})


def server_error(request):
    type, value, traceback = sys.exc_info()
    return render(request, 'error/500.html', dict(
        type=type.__name__,
        message=value,
    ))
