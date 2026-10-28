import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.chat.serializers.conversation_serializers import (
    ConversationDetailSerializer,
)

logger = logging.getLogger(__name__)

ERROR_EVENT = "chat.error"

MESSAGE_CREATED = "chat_message"
CONVERSATION_ASSIGNED = "conversation_assigned"
CONVERSATION_CLOSED = "conversation_closed"


def conversation_group_name(
    conversation_id: str,
) -> str:
    """
    Return Channels group name for conversation.
    """

    return f"conversation_{conversation_id}"


def build_message_created_event(payload: dict) -> dict:
    """
    Broadcast newly created message.

    `payload` — allaqachon serializatsiya qilingan xabar
    (`message_services.serialize_message`), chunki serializatsiya DB ga
    murojaat qiladi va async consumer ichida bajarilmaydi.
    """

    return {
        "type": MESSAGE_CREATED,
        "message": payload,
    }


def build_conversation_event(conversation, event: str) -> dict:
    """
    Chat holati o'zgarganini (olindi / yopildi) bildiruvchi payload.
    """

    return {
        "type": event,
        "conversation": ConversationDetailSerializer(conversation).data,
    }


def build_error_event(message: str) -> dict:
    """
    Standard websocket error payload.
    """

    return {
        "type": ERROR_EVENT,
        "message": message,
    }


def broadcast_conversation_event(*, conversation, event: str) -> None:
    """
    Chat guruhiga holat o'zgarganini yuborish.

    Har doim `transaction.on_commit()` ichidan chaqiriladi — tranzaksiya
    orqaga qaytsa, mijozlarga yolg'on xabar ketmasligi uchun.

    Channel layer (Redis) ishlamay qolsa ham asosiy amaliyot (chat olindi /
    yopildi) allaqachon bazaga yozilgan, shuning uchun xato faqat log'ga
    yoziladi va yuqoriga ko'tarilmaydi.
    """

    try:
        channel_layer = get_channel_layer()

        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            conversation_group_name(conversation.id),
            build_conversation_event(conversation, event),
        )

    except Exception:
        logger.exception(
            "[CHAT] broadcast failed: event=%s conversation=%s",
            event,
            conversation.id,
        )


def user_group_name(user_id) -> str:
    """Foydalanuvchining barcha ochiq chat soketlari guruhi (logout'da yopish uchun)."""
    return f"user_{user_id}"


def close_user_sockets(user_id) -> None:
    """
    Logout / parol o'zgarishi / bloklashdan keyin shu foydalanuvchining ochiq
    WebSocket'larini yopish (audit F1: aks holda soket xabarlarni olishda davom etardi).
    Channel layer ishlamasa — jim o'tadi, logout buzilmaydi.
    """
    import logging
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(user_group_name(user_id), {"type": "force.logout"})
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("WS yopish xabari yuborilmadi (user=%s): %s", user_id, exc)
