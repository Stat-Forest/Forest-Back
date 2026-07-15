from django.contrib import admin
from django.db.models import Count

from apps.base.admin import admin_site
from apps.chat.models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    fields = (
        "sender",
        "text",
        "is_read",
        "created_at",
    )
    readonly_fields = (
        "sender",
        "text",
        "is_read",
        "created_at",
    )
    ordering = ("created_at",)
    show_change_link = True


@admin.register(Conversation, site=admin_site)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "assigned_to",
        "status",
        "messages_count",
        "last_message_at",
        "taken_at",
        "closed_at",
        "created_at",
    )

    list_filter = (
        "status",
        "assigned_to",
        "created_at",
        "taken_at",
        "closed_at",
    )

    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "assigned_to__first_name",
        "assigned_to__last_name",
        "assigned_to__email",
    )

    autocomplete_fields = (
        "user",
        "assigned_to",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "taken_at",
        "closed_at",
        "last_message_at",
    )

    ordering = (
        "-last_message_at",
        "-created_at",
    )

    date_hierarchy = "created_at"

    list_select_related = (
        "user",
        "assigned_to",
    )

    inlines = [
        MessageInline,
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related(
            "user",
            "assigned_to",
        ).annotate(
            _messages_count=Count("messages")
        )

    @admin.display(description="Messages")
    def messages_count(self, obj):
        return obj._messages_count


@admin.register(Message, site=admin_site)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "sender",
        "short_text",
        "is_read",
        "created_at",
    )

    list_filter = (
        "is_read",
        "created_at",
    )

    search_fields = (
        "text",
        "sender__first_name",
        "sender__last_name",
        "sender__email",
        "=conversation__id",
    )

    autocomplete_fields = (
        "conversation",
        "sender",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_select_related = (
        "conversation",
        "sender",
    )

    @admin.display(description="Message")
    def short_text(self, obj):
        if len(obj.text) <= 80:
            return obj.text
        return f"{obj.text[:80]}..."