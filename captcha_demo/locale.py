"""Choose the language of each request.

1. An explicit choice wins: the EN | TR switch posts to Django's ``set_language`` view,
   which stores it in the ``django_language`` cookie.
2. API clients (``/api/...``) may ask with the standard ``Accept-Language`` header.
3. Everything else is English, also for browsers that prefer Turkish, so the demo looks
   the same to every first-time visitor.

Django's own ``LocaleMiddleware`` would apply ``Accept-Language`` to the HTML pages too,
which is why this small middleware replaces it.
"""

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import translation
from django.utils.cache import patch_vary_headers


def language_for(request: HttpRequest) -> str:
    supported = {code for code, _name in settings.LANGUAGES}
    chosen = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
    if chosen in supported:
        return chosen
    if request.path.startswith("/api/"):
        return translation.get_language_from_request(request)
    return settings.LANGUAGE_CODE


class LanguageMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        language = language_for(request)
        translation.activate(language)
        request.LANGUAGE_CODE = language
        try:
            response = self.get_response(request)
        finally:
            translation.deactivate()
        response.headers.setdefault("Content-Language", language)
        patch_vary_headers(response, ("Cookie", "Accept-Language"))
        return response
