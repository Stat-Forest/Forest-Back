from django.urls import path

from apps.chat.websocket.consumers import ChatConsumer


websocket_urlpatterns = [
    path(
        "ws/chat/<uuid:conversation_id>/",
        ChatConsumer.as_asgi(),
    ),
]