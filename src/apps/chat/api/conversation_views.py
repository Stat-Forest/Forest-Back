from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.chat.exceptions import ChatException
from apps.chat.selectors.conversation_selectors import (
    get_assigned_conversations,
    get_conversation_by_id,
    get_new_conversations,
    get_user_conversations, get_accessible_conversation,
)
from apps.chat.serializers.conversation_serializers import (
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
)
from apps.chat.services.conversation_services import (
    assign_conversation,
    close_conversation,
    create_conversation,
)


class ConversationCreateAPIView(GenericAPIView):
    """
    Create new support conversation.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        try:
            conversation = create_conversation(
                user=request.user,
            )

        except ChatException as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = ConversationDetailSerializer(
            conversation,
            context=self.get_serializer_context(),
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ConversationListAPIView(GenericAPIView):
    """
    List current user's conversations.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationListSerializer

    def get(self, request, *args, **kwargs):
        conversations = get_user_conversations(
            request.user,
        )

        serializer = self.get_serializer(
            conversations,
            many=True,
        )

        return Response(serializer.data)


class ConversationDetailAPIView(GenericAPIView):
    """
    Retrieve conversation details.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationDetailSerializer

    def get(self, request, conversation_id, *args, **kwargs):
        conversation = get_accessible_conversation(
            conversation_id=conversation_id,
            user=request.user,
        )

        if conversation is None:
            return Response(
                {
                    "detail": "Conversation not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(
            conversation,
        )

        return Response(serializer.data)


class SupportNewConversationListAPIView(GenericAPIView):
    """
    List waiting conversations.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationListSerializer

    def get(self, request, *args, **kwargs):
        conversations = get_new_conversations()

        serializer = self.get_serializer(
            conversations,
            many=True,
        )

        return Response(serializer.data)


class SupportMyConversationListAPIView(GenericAPIView):
    """
    List assigned conversations.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationListSerializer

    def get(self, request, *args, **kwargs):
        conversations = get_assigned_conversations(
            request.user,
        )

        serializer = self.get_serializer(
            conversations,
            many=True,
        )

        return Response(serializer.data)


class AssignConversationAPIView(GenericAPIView):
    """
    Assign conversation to support admin.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, conversation_id, *args, **kwargs):
        try:
            conversation = assign_conversation(
                conversation_id=conversation_id,
                support_admin=request.user,
            )

        except ChatException as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ConversationDetailSerializer(
            conversation,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data)


class CloseConversationAPIView(GenericAPIView):
    """
    Close support conversation.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, conversation_id, *args, **kwargs):
        try:
            conversation = close_conversation(
                conversation_id=conversation_id,
                support_admin=request.user,
            )

        except ChatException as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ConversationDetailSerializer(
            conversation,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data)