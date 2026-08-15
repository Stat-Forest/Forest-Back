"""
Chat modulining asosiy invariantlari.

Bu testlar aynan tuzatilgan buglarni qorovullaydi — nomlaridagi
K1/K2/K4/J1/J2/J4 belgilari fix rejasidagi raqamlarga mos keladi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.exceptions import (
    ConversationAccessDenied,
    ConversationAlreadyExists,
    ConversationLimitExceeded,
    MessageTooLong,
    SupportPermissionDenied,
)
from apps.chat.models import Conversation, Message
from apps.chat.models.chat import MAX_MESSAGE_LENGTH
from apps.chat.services.conversation_services import (
    assign_conversation,
    cancel_conversation,
    close_conversation,
    create_conversation,
)
from apps.chat.services.message_services import (
    mark_conversation_as_read,
    send_message,
    validate_conversation_access,
)
from apps.chat.websocket.consumers import ChatConsumer
from apps.chat.websocket.events import (
    CONVERSATION_ASSIGNED,
    CONVERSATION_CLOSED,
    conversation_group_name,
)

User = get_user_model()

IN_MEMORY_CHANNELS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}


def make_user(email, role, **extra):
    return User.objects.create_user(
        email=email,
        password="TestPassword123!",
        first_name="Test",
        last_name=role,
        role=role,
        **extra,
    )


class ChatTestMixin:
    def setUp(self):
        super().setUp()
        self.user = make_user("user@example.com", User.Role.TASHKILOT_HODIMI)
        self.other_user = make_user("other@example.com", User.Role.TASHKILOT_HODIMI)
        self.support = make_user("support@example.com", User.Role.SUPPORT_ADMIN)
        self.support2 = make_user("support2@example.com", User.Role.SUPPORT_ADMIN)


class SupportAdminPermissionTests(ChatTestMixin, TestCase):
    """K1 — support admin chatni ola/yopa olishi shart."""

    def test_support_admin_can_assign_and_close(self):
        conversation = create_conversation(user=self.user)

        assigned = assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )
        self.assertEqual(assigned.status, Conversation.Status.TAKEN)
        self.assertEqual(assigned.assigned_to_id, self.support.id)
        self.assertIsNotNone(assigned.taken_at)

        closed = close_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )
        self.assertEqual(closed.status, Conversation.Status.CLOSED)
        self.assertIsNotNone(closed.closed_at)

    def test_assign_updates_updated_at(self):
        """O3 — assign paytida updated_at DB da yangilanishi kerak."""
        conversation = create_conversation(user=self.user)
        before = Conversation.objects.get(pk=conversation.pk).updated_at

        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )

        after = Conversation.objects.get(pk=conversation.pk).updated_at
        self.assertGreater(after, before)

    def test_regular_user_cannot_assign(self):
        conversation = create_conversation(user=self.user)

        with self.assertRaises(SupportPermissionDenied):
            assign_conversation(
                conversation_id=conversation.id,
                support_admin=self.other_user,
            )

    def test_second_admin_cannot_take_taken_conversation(self):
        conversation = create_conversation(user=self.user)
        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )

        with self.assertRaises(Exception):
            assign_conversation(
                conversation_id=conversation.id,
                support_admin=self.support2,
            )

    def test_other_admin_cannot_close_someone_elses_conversation(self):
        conversation = create_conversation(user=self.user)
        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )

        with self.assertRaises(ConversationAccessDenied):
            close_conversation(
                conversation_id=conversation.id,
                support_admin=self.support2,
            )

    def test_supervisor_can_force_close_unassigned_conversation(self):
        """K4 — tashlab ketilgan NEW chatni super_admin yopa olsin."""
        supervisor = make_user(
            "boss@example.com",
            User.Role.SUPER_ADMIN,
            is_superuser=True,
            is_staff=True,
        )
        conversation = create_conversation(user=self.user)

        closed = close_conversation(
            conversation_id=conversation.id,
            support_admin=supervisor,
        )
        self.assertEqual(closed.status, Conversation.Status.CLOSED)


class ConversationLimitTests(ChatTestMixin, TestCase):
    """Asosiy talab — kuniga 2 ta chat, undan ko'p emas."""

    def test_two_conversations_can_wait_in_queue(self):
        """K4 — olinmagan NEW chat ikkinchisini ochishga to'sqinlik qilmaydi."""
        create_conversation(user=self.user)
        create_conversation(user=self.user)

        self.assertEqual(
            Conversation.objects.filter(user=self.user).count(),
            2,
        )

        with self.assertRaises(ConversationAlreadyExists):
            create_conversation(user=self.user)

    def test_daily_limit_is_two(self):
        first = create_conversation(user=self.user)
        assign_conversation(conversation_id=first.id, support_admin=self.support)
        close_conversation(conversation_id=first.id, support_admin=self.support)

        second = create_conversation(user=self.user)
        assign_conversation(conversation_id=second.id, support_admin=self.support)
        close_conversation(conversation_id=second.id, support_admin=self.support)

        # Ikkalasi ham yopilgan — faol chat yo'q, lekin kunlik kvota tugagan.
        with self.assertRaises(ConversationLimitExceeded):
            create_conversation(user=self.user)

    def test_taken_conversation_blocks_new_one(self):
        conversation = create_conversation(user=self.user)
        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )

        with self.assertRaises(ConversationAlreadyExists):
            create_conversation(user=self.user)

    def test_limit_is_per_user(self):
        create_conversation(user=self.user)
        create_conversation(user=self.user)

        # Boshqa foydalanuvchi ta'sirlanmaydi.
        self.assertIsNotNone(create_conversation(user=self.other_user))


class CancelConversationTests(ChatTestMixin, TestCase):
    """K4 — user o'zining olinmagan chatini bekor qila oladi."""

    def test_user_can_cancel_own_new_conversation(self):
        conversation = create_conversation(user=self.user)

        cancelled = cancel_conversation(
            conversation_id=conversation.id,
            user=self.user,
        )
        self.assertEqual(cancelled.status, Conversation.Status.CLOSED)

    def test_user_cannot_cancel_taken_conversation(self):
        conversation = create_conversation(user=self.user)
        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )

        with self.assertRaises(ConversationAccessDenied):
            cancel_conversation(
                conversation_id=conversation.id,
                user=self.user,
            )

    def test_user_cannot_cancel_someone_elses_conversation(self):
        conversation = create_conversation(user=self.user)

        with self.assertRaises(ConversationAccessDenied):
            cancel_conversation(
                conversation_id=conversation.id,
                user=self.other_user,
            )

    def test_cancel_does_not_refund_daily_quota(self):
        first = create_conversation(user=self.user)
        cancel_conversation(conversation_id=first.id, user=self.user)

        second = create_conversation(user=self.user)
        cancel_conversation(conversation_id=second.id, user=self.user)

        with self.assertRaises(ConversationLimitExceeded):
            create_conversation(user=self.user)


class MessageAccessTests(ChatTestMixin, TestCase):
    """J4 — o'qish kengroq, yozish tor."""

    def test_support_admin_can_read_unassigned_conversation(self):
        conversation = create_conversation(user=self.user)
        send_message(
            conversation_id=conversation.id,
            sender=self.user,
            text="Yordam kerak",
        )

        # Istisno ko'tarilmasligi kerak — admin savolni o'qiy olsin.
        validate_conversation_access(
            conversation=conversation,
            user=self.support,
        )

    def test_support_admin_cannot_write_to_unassigned_conversation(self):
        conversation = create_conversation(user=self.user)

        with self.assertRaises(ConversationAccessDenied):
            send_message(
                conversation_id=conversation.id,
                sender=self.support,
                text="Salom",
            )

    def test_other_admin_cannot_write_to_assigned_conversation(self):
        conversation = create_conversation(user=self.user)
        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )

        with self.assertRaises(ConversationAccessDenied):
            send_message(
                conversation_id=conversation.id,
                sender=self.support2,
                text="Salom",
            )

    def test_assigned_admin_can_write(self):
        conversation = create_conversation(user=self.user)
        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )

        message = send_message(
            conversation_id=conversation.id,
            sender=self.support,
            text="Assalomu alaykum",
        )
        self.assertEqual(message.sender_id, self.support.id)

    def test_unrelated_user_cannot_read(self):
        conversation = create_conversation(user=self.user)

        with self.assertRaises(ConversationAccessDenied):
            validate_conversation_access(
                conversation=conversation,
                user=self.other_user,
            )

    def test_message_too_long_is_rejected(self):
        """J2 — 5000 belgidan uzun xabar bazaga tushmasligi kerak."""
        conversation = create_conversation(user=self.user)

        with self.assertRaises(MessageTooLong):
            send_message(
                conversation_id=conversation.id,
                sender=self.user,
                text="a" * (MAX_MESSAGE_LENGTH + 1),
            )

        self.assertEqual(Message.objects.count(), 0)

    def test_last_message_at_matches_message(self):
        conversation = create_conversation(user=self.user)
        message = send_message(
            conversation_id=conversation.id,
            sender=self.user,
            text="salom",
        )

        conversation.refresh_from_db()
        self.assertEqual(conversation.last_message_at, message.created_at)

    def test_mark_as_read_only_marks_other_side(self):
        conversation = create_conversation(user=self.user)
        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )
        mine = send_message(
            conversation_id=conversation.id,
            sender=self.user,
            text="savol",
        )
        theirs = send_message(
            conversation_id=conversation.id,
            sender=self.support,
            text="javob",
        )

        marked = mark_conversation_as_read(
            conversation_id=conversation.id,
            user=self.user,
        )

        mine.refresh_from_db()
        theirs.refresh_from_db()
        self.assertEqual(marked, 1)
        self.assertFalse(mine.is_read)
        self.assertTrue(theirs.is_read)


class ChatAPITests(ChatTestMixin, TestCase):
    """K2 — support endpointlari rol bilan yopilgan."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_regular_user_cannot_list_new_conversations(self):
        create_conversation(user=self.user)

        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse("support-new-conversations"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_support_admin_can_list_new_conversations(self):
        create_conversation(user=self.user)

        self.client.force_authenticate(user=self.support)
        response = self.client.get(reverse("support-new-conversations"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_regular_user_cannot_list_support_queue_of_others(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse("support-my-conversations"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_daily_limit_returns_429(self):
        """O1 — limit xatosi endi 400 emas, 429 qaytadi."""
        first = create_conversation(user=self.user)
        assign_conversation(conversation_id=first.id, support_admin=self.support)
        close_conversation(conversation_id=first.id, support_admin=self.support)

        second = create_conversation(user=self.user)
        assign_conversation(conversation_id=second.id, support_admin=self.support)
        close_conversation(conversation_id=second.id, support_admin=self.support)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("conversation-create"))

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def test_foreign_conversation_messages_return_403(self):
        conversation = create_conversation(user=self.user)

        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(
            reverse(
                "conversation-messages",
                kwargs={"conversation_id": conversation.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_messages_endpoint_is_paginated(self):
        """J5 — tarix endi sahifalanadi."""
        conversation = create_conversation(user=self.user)
        send_message(
            conversation_id=conversation.id,
            sender=self.user,
            text="salom",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse(
                "conversation-messages",
                kwargs={"conversation_id": conversation.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 1)

    def test_conversation_list_reports_unread_count(self):
        conversation = create_conversation(user=self.user)
        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )
        send_message(
            conversation_id=conversation.id,
            sender=self.support,
            text="javob",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("conversation-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["unread_count"], 1)

    def test_user_can_cancel_via_api(self):
        conversation = create_conversation(user=self.user)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse(
                "conversation-cancel",
                kwargs={"conversation_id": conversation.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Conversation.Status.CLOSED)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNELS)
class ConversationBroadcastTests(ChatTestMixin, TestCase):
    """O7 — assign/close hodisalari guruhga yetib borishi kerak."""

    def _subscribe(self, conversation):
        layer = get_channel_layer()
        channel_name = async_to_sync(layer.new_channel)()
        async_to_sync(layer.group_add)(
            conversation_group_name(conversation.id),
            channel_name,
        )
        return layer, channel_name

    def test_assign_broadcasts_event(self):
        conversation = create_conversation(user=self.user)
        layer, channel_name = self._subscribe(conversation)

        with self.captureOnCommitCallbacks(execute=True):
            assign_conversation(
                conversation_id=conversation.id,
                support_admin=self.support,
            )

        event = async_to_sync(layer.receive)(channel_name)
        self.assertEqual(event["type"], CONVERSATION_ASSIGNED)
        self.assertEqual(
            event["conversation"]["status"],
            Conversation.Status.TAKEN,
        )

    def test_close_broadcasts_event(self):
        conversation = create_conversation(user=self.user)
        assign_conversation(
            conversation_id=conversation.id,
            support_admin=self.support,
        )
        layer, channel_name = self._subscribe(conversation)

        with self.captureOnCommitCallbacks(execute=True):
            close_conversation(
                conversation_id=conversation.id,
                support_admin=self.support,
            )

        event = async_to_sync(layer.receive)(channel_name)
        self.assertEqual(event["type"], CONVERSATION_CLOSED)
        self.assertEqual(
            event["conversation"]["status"],
            Conversation.Status.CLOSED,
        )


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNELS)
class ChatConsumerTests(TransactionTestCase):
    """J1 — buzuq payload soketni yiqitmasligi kerak."""

    def setUp(self):
        super().setUp()
        self.user = make_user("wsuser@example.com", User.Role.TASHKILOT_HODIMI)
        self.conversation = create_conversation(user=self.user)

    async def _connect(self):
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.conversation.id}/",
        )
        communicator.scope["user"] = self.user
        communicator.scope["url_route"] = {
            "kwargs": {"conversation_id": self.conversation.id}
        }

        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        return communicator

    async def test_invalid_json_does_not_kill_socket(self):
        communicator = await self._connect()

        await communicator.send_to(text_data="{not json")
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.error")

        # Soket hali tirik — normal xabar o'tishi kerak.
        await communicator.send_json_to({"text": "salom"})
        message_event = await communicator.receive_json_from()
        self.assertEqual(message_event["type"], "chat_message")
        self.assertEqual(message_event["message"]["text"], "salom")

        await communicator.disconnect()

    async def test_non_object_payload_does_not_kill_socket(self):
        communicator = await self._connect()

        await communicator.send_json_to([1, 2, 3])
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.error")

        await communicator.disconnect()

    async def test_empty_text_returns_error(self):
        communicator = await self._connect()

        await communicator.send_json_to({"text": "   "})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.error")

        await communicator.disconnect()

    async def test_oversized_message_is_rejected_over_websocket(self):
        communicator = await self._connect()

        await communicator.send_json_to(
            {"text": "a" * (MAX_MESSAGE_LENGTH + 1)}
        )
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.error")

        await communicator.disconnect()
