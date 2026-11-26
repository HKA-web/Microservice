import logging

from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger(__name__)


def ExceptionHandler(exception, context):
    response = exception_handler(exception, context)
    if not response and isinstance(exception, IntegrityError):
        if 'duplicate key value violates unique constraint' in str(exception):
            set_rollback()
            message = 'Unique constraint violated: {exception}'.format(exception=exception)
            response = Response(dict(error=message), status=400)
    if response is None:
        set_rollback()
        logger.exception(exception)
        response = Response(dict(error=str(exception)), status=500)
    return response
