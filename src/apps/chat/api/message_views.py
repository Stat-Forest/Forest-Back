from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.chat.selectors.message_selectors import (
    get_conversation_messages,
)
from apps.chat.serializers.message_serializers import (
    MessageSerializer,
)
from apps.chat.services.message_services import (
    get_conversation_or_raise,
    mark_conversation_as_read,
    validate_conversation_access,
)


class ConversationMessagesAPIView(GenericAPIView):
    """
    Return messages of a conversation (paginated).
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = MessageSerializer

    @extend_schema(
        tags=["Chat - User", "Chat - Support"],
        summary="Get messages of a conversation (marks them as read)",
    )
    def get(self, request, conversation_id, *args, **kwargs):
        conversation = get_conversation_or_raise(
            conversation_id=conversation_id,
        )

        validate_conversation_access(
            conversation=conversation,
            user=request.user,
        )

        # O'qilgan deb belgilash serializatsiyadan OLDIN bajariladi:
        # queryset lazy bo'lgani uchun aks holda javobdagi `is_read`
        # qiymatlari yozuv tartibiga bog'lib qolardi.
        mark_conversation_as_read(
            conversation_id=conversation.id,
            user=request.user,
        )

        messages = get_conversation_messages(conversation)

        page = self.paginate_queryset(messages)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(messages, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class MarkConversationReadAPIView(GenericAPIView):
    """
    Mark all unread messages in a conversation as read,
    WITHOUT re-fetching full message history.

    Lightweight alternative to calling
    GET /conversations/<id>/messages/ again just to
    refresh read status.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["Chat - User", "Chat - Support"],
        summary="Mark unread messages as read without refetching history",
        request=None,
        responses={
            200: inline_serializer(
                name="MarkConversationReadResponse",
                fields={"marked_count": serializers.IntegerField()},
            )
        },
    )
    def post(self, request, conversation_id, *args, **kwargs):
        marked_count = mark_conversation_as_read(
            conversation_id=conversation_id,
            user=request.user,
        )

        return Response(
            {"marked_count": marked_count},
            status=status.HTTP_200_OK,
        )
