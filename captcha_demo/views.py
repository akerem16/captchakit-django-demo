from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html")


def client_ip_debug(request: HttpRequest) -> JsonResponse:
    """TEMPORARY: echo the requester's own proxy headers to calibrate TRUSTED_PROXY_COUNT."""
    keys = ("REMOTE_ADDR", "HTTP_X_FORWARDED_FOR", "HTTP_CF_CONNECTING_IP", "HTTP_TRUE_CLIENT_IP")
    return JsonResponse({key: request.META.get(key) for key in keys})
