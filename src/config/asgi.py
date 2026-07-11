"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()  # django.setup() shu yerda ishlaydi

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.chat.websocket.routing import websocket_urlpatterns
from apps.chat.websocket.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
})
