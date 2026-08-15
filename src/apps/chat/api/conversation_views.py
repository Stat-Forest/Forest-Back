from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.chat.permissions import IsSupportAdmin
from apps.chat.selectors.conversation_selectors import (
    get_accessible_conversation,
    get_assigned_conversations,
    get_new_conversations,
    get_user_conversations,
)
from apps.chat.serializers.conversation_serializers import (
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
)
from apps.chat.services.conversation_services import (
    assign_conversation,
    cancel_conversation,
    close_conversation,
    create_conversation,
)


class ConversationListMixin:
    """
    Chat ro'yxatlari uchun umumiy pagination + serializatsiya.
    """

    serializer_class = ConversationListSerializer

    def list_conversations(self, queryset):
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ConversationCreateAPIView(GenericAPIView):
    """
    Create new support conversation.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationCreateSerializer

    @extend_schema(
        tags=["Chat - User"],
        summary="Create a new support conversation",
        responses={201: ConversationDetailSerializer},
    )
    def post(self, request, *args, **kwargs):
        conversation = create_conversation(
            user=request.user,
        )

        response_serializer = ConversationDetailSerializer(
            conversation,
            context=self.get_serializer_context(),
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ConversationListAPIView(ConversationListMixin, GenericAPIView):
    """
    List current user's conversations.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["Chat - User"],
        summary="List current user's conversations",
    )
    def get(self, request, *args, **kwargs):
        return self.list_conversations(
            get_user_conversations(request.user)
        )


class ConversationDetailAPIView(GenericAPIView):
    """
    Retrieve conversation details.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationDetailSerializer

    @extend_schema(
        tags=["Chat - User", "Chat - Support"],
        summary="Retrieve conversation details",
    )
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


class SupportNewConversationListAPIView(ConversationListMixin, GenericAPIView):
    """
    List waiting conversations.
    """

    permission_classes = (IsAuthenticated, IsSupportAdmin)

    @extend_schema(
        tags=["Chat - Support"],
        summary="List conversations waiting for a support administrator",
    )
    def get(self, request, *args, **kwargs):
        return self.list_conversations(
            get_new_conversations(request.user)
        )


class SupportMyConversationListAPIView(ConversationListMixin, GenericAPIView):
    """
    List assigned conversations.
    """

    permission_classes = (IsAuthenticated, IsSupportAdmin)

    @extend_schema(
        tags=["Chat - Support"],
        summary="List conversations assigned to current support administrator",
    )
    def get(self, request, *args, **kwargs):
        return self.list_conversations(
            get_assigned_conversations(request.user)
        )


class AssignConversationAPIView(GenericAPIView):
    """
    Assign conversation to support admin.
    """

    permission_classes = (IsAuthenticated, IsSupportAdmin)
    serializer_class = ConversationDetailSerializer

    @extend_schema(
        tags=["Chat - Support"],
        summary="Assign a conversation to current support administrator",
        request=None,
    )
    def post(self, request, conversation_id, *args, **kwargs):
        conversation = assign_conversation(
            conversation_id=conversation_id,
            support_admin=request.user,
        )

        serializer = self.get_serializer(conversation)

        return Response(serializer.data)


class CloseConversationAPIView(GenericAPIView):
    """
    Close support conversation.
    """

    permission_classes = (IsAuthenticated, IsSupportAdmin)
    serializer_class = ConversationDetailSerializer

    @extend_schema(
        tags=["Chat - Support"],
        summary="Close an assigned conversation",
        request=None,
    )
    def post(self, request, conversation_id, *args, **kwargs):
        conversation = close_conversation(
            conversation_id=conversation_id,
            support_admin=request.user,
        )

        serializer = self.get_serializer(conversation)

        return Response(serializer.data)


class CancelConversationAPIView(GenericAPIView):
    """
    Cancel own conversation while it is still waiting.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationDetailSerializer

    @extend_schema(
        tags=["Chat - User"],
        summary="Cancel your own conversation that no admin has taken yet",
        request=None,
    )
    def post(self, request, conversation_id, *args, **kwargs):
        conversation = cancel_conversation(
            conversation_id=conversation_id,
            user=request.user,
        )

        serializer = self.get_serializer(conversation)

        return Response(serializer.data)
