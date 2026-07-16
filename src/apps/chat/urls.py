from django.urls import path

from apps.chat.api.conversation_views import (
    AssignConversationAPIView,
    CloseConversationAPIView,
    ConversationCreateAPIView,
    ConversationDetailAPIView,
    ConversationListAPIView,
    SupportMyConversationListAPIView,
    SupportNewConversationListAPIView,
)
from apps.chat.api.message_views import (
    ConversationMessagesAPIView, MarkConversationReadAPIView,
)

urlpatterns = [
    # ===============================
    # User
    # ===============================
    path(
        "conversations/",
        ConversationCreateAPIView.as_view(),
        name="conversation-create",
    ),

    path(
        "conversations/list/",
        ConversationListAPIView.as_view(),
        name="conversation-list",
    ),

    path(
        "conversations/<uuid:conversation_id>/",
        ConversationDetailAPIView.as_view(),
        name="conversation-detail",
    ),

    path(
        "conversations/<uuid:conversation_id>/messages/",
        ConversationMessagesAPIView.as_view(),
        name="conversation-messages",
    ),

    path(
        "conversations/<uuid:conversation_id>/mark-read/",
        MarkConversationReadAPIView.as_view(),
        name="conversation-mark-read",
    ),

    # ===============================
    # Support
    # ===============================
    path(
        "support/new/",
        SupportNewConversationListAPIView.as_view(),
        name="support-new-conversations",
    ),

    path(
        "support/my/",
        SupportMyConversationListAPIView.as_view(),
        name="support-my-conversations",
    ),

    path(
        "conversations/<uuid:conversation_id>/assign/",
        AssignConversationAPIView.as_view(),
        name="conversation-assign",
    ),

    path(
        "conversations/<uuid:conversation_id>/close/",
        CloseConversationAPIView.as_view(),
        name="conversation-close",
    ),
]
