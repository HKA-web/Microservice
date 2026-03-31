from __future__ import annotations

import asyncio
import logging
from typing import Callable, Coroutine, Any

import minify_html
from django.http import HttpRequest
from django.http.response import HttpResponseBase
from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)


class MinifyMiddleware:
    sync_capable = True
    async_capable = True

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response
        if asyncio.iscoroutinefunction(self.get_response):
            self._is_coroutine = (asyncio.coroutines._is_coroutine)
        else:
            self._is_coroutine = None

    def __call__(self, request: HttpRequest) -> HttpResponseBase or Coroutine[Any, Any, Any]:
        if self._is_coroutine:
            return self.__acall__(request)
        response = self.get_response(request)
        self.maybe_minify(request, response)
        return response

    async def __acall__(self, request: HttpRequest) -> Coroutine[Any, Any, HttpResponseBase]:
        response = await self.get_response(request)
        self.maybe_minify(request, response)
        return response

    def maybe_minify(self, request: HttpRequest, response: HttpResponseBase) -> None:
        if self.should_minify(request, response):
            content = response.content.decode(response.charset)
            minified_content = minify_html.minify(content, **self.minify_args)
            response.content = minified_content
            if 'Content-Length' in response:
                response['Content-Length'] = len(minified_content)
            response['Minify'] = True

    minify_args = {
        'minify_css': True,
        'minify_js': True,
        'keep_comments': False,
    }

    def should_minify(self, request: HttpRequest, response: HttpResponseBase) -> bool:
        return (
            not getattr(response, 'streaming', False)
            and (request.resolver_match is None or getattr(request, 'minify', True))
            and response.get('Content-Encoding', '') == ''
            and (response.get('Content-Type', '').split(';', 1)[0] in ('text/html', 'text/javascript') or response.get('Content-Type', '') in ('text/html', 'text/javascript'))
            and getattr(djangosettings, 'COMPRESS_ENABLED', False)
        )
