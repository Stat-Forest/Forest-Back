from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.chat.websocket.events import conversation_group_name, ERROR_EVENT
from apps.chat.exceptions import (
    ConversationNotFound,
    ConversationAccessDenied,
    ChatException
)
from apps.chat.services import (
    get_conversation_or_raise,
    can_connect_to_conversation,
    send_message,
    serialize_message
)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
        WebSocket consumer for support chat.
    """

    async def connect(self):
        """
        Authenticate websocket connection and join conversation group.
        """

        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close(code=4401)
            return

        self.conversation_id = self.scope["url_route"]["kwargs"][
            "conversation_id"
        ]

        try:
            conversation = await database_sync_to_async(
                get_conversation_or_raise
            )(
                conversation_id=self.conversation_id,
            )

            await database_sync_to_async(
                can_connect_to_conversation
            )(
                conversation=conversation,
                user=self.user,
            )

        except ConversationNotFound:
            await self.close(code=4404)
            return

        except ConversationAccessDenied:
            await self.close(code=4403)
            return

        self.group_name = conversation_group_name(
            self.conversation_id,
        )

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def _send_error(self, message: str) -> None:
        """
            Send error message to websocket client.
        """
        await self.send_json(
            {
                "type": ERROR_EVENT,
                "message": message
            }
        )

    async def receive_json(
        self,
        content,
        **kwargs,
    ):
        """
        Receive websocket message.
        """

        text = content.get(
            "text",
            "",
        ).strip()

        if not text:
            await self._send_error(
                "Message cannot be empty.",
            )
            return

        try:
            message = await database_sync_to_async(
                send_message,
            )(
                conversation_id=self.conversation_id,
                sender=self.user,
                text=text,
            )

            payload = await database_sync_to_async(
                serialize_message,
            )(
                message=message,
            )

        except ChatException as exc:
            await self._send_error(
                str(exc),
            )
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "message": payload,
            },
        )

    async def chat_message(self, event):
        """
        Broadcast message to websocket clients.
        """
        await self.send_json(
            {
                "type": "chat_message",
                "message": event["message"],
            }
        )