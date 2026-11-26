from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from django.http.response import HttpResponseBase

logger = logging.getLogger(__name__)

ViewFunc = TypeVar('ViewFunc', bound=Callable[..., HttpResponseBase])


def nominify(view_func: ViewFunc) -> ViewFunc:
    @wraps(view_func)
    def wrapped(request, *args: Any, **kwargs: Any) -> HttpResponseBase:
        setattr(request, 'minify', False)
        return view_func(request, *args, **kwargs)

    return wrapped
