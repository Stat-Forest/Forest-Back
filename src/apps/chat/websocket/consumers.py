import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.chat.websocket.chat_serializers import SendMessageSerializer
from apps.chat.websocket.events import (
    CONVERSATION_ASSIGNED,
    CONVERSATION_CLOSED,
    MESSAGE_CREATED,
    build_error_event,
    build_message_created_event,
    conversation_group_name,
)
from apps.chat.exceptions import (
    ConversationNotFound,
    ConversationAccessDenied,
    ChatException
)
from apps.chat.services import (
    get_conversation_or_raise,
    validate_conversation_access,
    send_message,
    serialize_message
)

logger = logging.getLogger(__name__)


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
                validate_conversation_access
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

        # Mijoz ["jwt", token] subprotocol'larini yuboradi — brauzer server
        # ulardan bittasini qaytarishini talab qiladi, aks holda ulanishni uzadi.
        subprotocols = self.scope.get("subprotocols") or []
        await self.accept(subprotocol="jwt" if "jwt" in subprotocols else None)

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
        await self.send_json(build_error_event(message))

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        """
        Xom frame'ni qabul qilish.

        Bazaviy implementatsiya buzuq JSON yoki binary frame'da
        istisno ko'taradi va consumer'ni butunlay yiqitadi (ulanish
        uziladi). Bu yerda ular oddiy xato javobiga aylantiriladi —
        soket tirik qoladi.
        """

        if text_data is None:
            await self._send_error("Only text frames are supported.")
            return

        try:
            content = json.loads(text_data)

        except (json.JSONDecodeError, ValueError):
            await self._send_error("Invalid JSON payload.")
            return

        await self.receive_json(content, **kwargs)

    async def receive_json(
        self,
        content,
        **kwargs,
    ):
        """
        Receive websocket message.
        """

        if not isinstance(content, dict):
            await self._send_error("Payload must be a JSON object.")
            return

        serializer = SendMessageSerializer(data=content)

        if not serializer.is_valid():
            errors = serializer.errors.get("text") or ["Invalid payload."]
            await self._send_error(str(errors[0]))
            return

        text = serializer.validated_data["text"]

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

        except Exception:
            # Kutilmagan xato (DB uzilishi va h.k.) — soketni yiqitmaymiz,
            # aks holda mijoz sababini bilmay qayta ulanishga urinaveradi.
            logger.exception(
                "[CHAT] send_message failed: conversation=%s user=%s",
                self.conversation_id,
                getattr(self.user, "id", None),
            )
            await self._send_error("Message could not be delivered.")
            return

        await self.channel_layer.group_send(
            self.group_name,
            build_message_created_event(payload),
        )

    async def chat_message(self, event):
        """
        Broadcast message to websocket clients.
        """
        await self.send_json(
            {
                "type": MESSAGE_CREATED,
                "message": event["message"],
            }
        )

    async def conversation_assigned(self, event):
        """
        Chat support admin tomonidan olindi.
        """
        await self.send_json(
            {
                "type": CONVERSATION_ASSIGNED,
                "conversation": event["conversation"],
            }
        )

    async def conversation_closed(self, event):
        """
        Chat yopildi.
        """
        await self.send_json(
            {
                "type": CONVERSATION_CLOSED,
                "conversation": event["conversation"],
            }
        )
