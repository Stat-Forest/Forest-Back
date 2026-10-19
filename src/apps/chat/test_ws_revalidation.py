"""Audit B4: ochiq WebSocket logout / token muddati tugaganidan keyin ishlamasligi kerak."""
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.authentications.service.token_denylist import revoke_access_token
from apps.chat.models import Message
from apps.chat.services.conversation_services import create_conversation
from apps.chat.tests import IN_MEMORY_CHANNELS, make_user
from apps.chat.websocket.consumers import ChatConsumer
from apps.chat.websocket.middleware import JWTAuthMiddleware
from apps.users.models import CustomUser


class MiddlewareKeepsTokenTest(TransactionTestCase):
    def test_token_is_stored_in_scope_for_revalidation(self):
        user = make_user("ws_mw@example.com", CustomUser.Role.TASHKILOT_HODIMI)
        access = str(RefreshToken.for_user(user).access_token)
        captured = {}

        async def inner(scope, receive, send):
            captured.update(scope)

        async_to_sync(JWTAuthMiddleware(inner))(
            {"type": "websocket", "subprotocols": ["jwt", access], "query_string": b""}, None, None)
        self.assertEqual(captured.get("jwt_token"), access)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNELS)
class WebSocketRevalidationTests(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("ws_revalidate@example.com", CustomUser.Role.TASHKILOT_HODIMI)
        self.conversation = create_conversation(user=self.user)
        self.access = str(RefreshToken.for_user(self.user).access_token)

    async def _connect(self):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.conversation.id}/")
        communicator.scope["user"] = self.user
        communicator.scope["jwt_token"] = self.access
        communicator.scope["url_route"] = {"kwargs": {"conversation_id": self.conversation.id}}
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        return communicator

    async def test_message_after_logout_is_rejected_and_socket_closed(self):
        communicator = await self._connect()
        await communicator.send_json_to({"text": "salom"})
        self.assertEqual((await communicator.receive_json_from())["type"], "chat_message")

        await database_sync_to_async(revoke_access_token)(AccessToken(self.access))

        await communicator.send_json_to({"text": "logoutdan keyin"})
        self.assertEqual((await communicator.receive_json_from())["type"], "chat.error")
        self.assertEqual((await communicator.receive_output())["type"], "websocket.close")
        count = await database_sync_to_async(
            Message.objects.filter(conversation=self.conversation, text="logoutdan keyin").count)()
        self.assertEqual(count, 0)
