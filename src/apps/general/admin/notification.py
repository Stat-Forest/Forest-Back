from django.contrib import admin
from apps.general.models import Notification
from apps.logs.mixins import AdminHistoryMixin


@admin.register(Notification)
class NotificationAdmin(AdminHistoryMixin,admin.ModelAdmin):
    list_display = ("date", "text_uz", "text_ru")
    search_fields = ("text_uz", "text_ru")
    list_filter = ("date",)
    ordering = ("-date",)

    fields = ("date", "text_uz", "text_ru")

