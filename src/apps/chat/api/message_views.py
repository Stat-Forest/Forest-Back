from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.chat.exceptions import (
    ChatException,
    ConversationNotFound,
)
from apps.chat.selectors.conversation_selectors import (
    get_conversation_by_id,
)
from apps.chat.selectors.message_selectors import (
    get_conversation_messages,
)
from apps.chat.serializers.message_serializers import (
    MessageSerializer,
)
from apps.chat.services.message_services import (
    mark_conversation_as_read,
)


class ConversationMessagesAPIView(GenericAPIView):
    """
    Return all messages of a conversation.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = MessageSerializer

    @extend_schema(
        tags=["Chat - User", "Chat - Support"],
        summary="Get all messages of a conversation (marks them as read)",
    )
    def get(self, request, conversation_id, *args, **kwargs):
        conversation = get_conversation_by_id(conversation_id)

        if conversation is None:
            return Response(
                {"detail": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if (
                request.user.id != conversation.user_id
                and request.user.id != conversation.assigned_to_id
        ):
            return Response(
                {"detail": "You don't have access to this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        messages = get_conversation_messages(conversation)
        serializer = self.get_serializer(messages, many=True)

        try:
            mark_conversation_as_read(
                conversation_id=conversation.id,
                user=request.user,
            )
        except ChatException:
            # o'qishni belgilash muvaffaqiyatsiz bo'lsa ham,
            # xabarlarni ko'rsatishga xalaqit bermasin
            pass

        return Response(serializer.data, status=status.HTTP_200_OK)

    # def get(
    #     self,
    #     request,
    #     conversation_id,
    #     *args,
    #     **kwargs,
    # ):
    #     conversation = get_conversation_by_id(
    #         conversation_id,
    #     )
    #
    #     if conversation is None:
    #         raise ConversationNotFound(
    #             "Conversation not found."
    #         )
    #
    #     if (
    #         request.user.id != conversation.user_id
    #         and request.user.id != conversation.assigned_to_id
    #     ):
    #         raise ChatException(
    #             "You don't have access to this conversation."
    #         )
    #
    #     messages = get_conversation_messages(
    #         conversation,
    #     )
    #
    #     serializer = self.get_serializer(
    #         messages,
    #         many=True,
    #     )
    #
    #     mark_conversation_as_read(
    #         conversation_id=conversation.id,
    #         user=request.user,
    #     )
    #
    #     return Response(
    #         serializer.data,
    #         status=status.HTTP_200_OK,
    #     )


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
    )
    def post(self, request, conversation_id, *args, **kwargs):
        conversation = get_conversation_by_id(conversation_id)

        if conversation is None:
            return Response(
                {"detail": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if (
                request.user.id != conversation.user_id
                and request.user.id != conversation.assigned_to_id
        ):
            return Response(
                {"detail": "You don't have access to this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            marked_count = mark_conversation_as_read(
                conversation_id=conversation.id,
                user=request.user,
            )

        except ChatException as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"marked_count": marked_count},
            status=status.HTTP_200_OK,
        )