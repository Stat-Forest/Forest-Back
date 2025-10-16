from django.contrib import admin
from django.utils.timezone import now
from apps.general.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("date", "text_uz","text_ru")
    search_fields = ('text_uz', 'text_ru')
    list_filter = ("date",)
    ordering = ("-date",)

    def get_queryset(self, request):
        """
        Faqat bugungi sanaga teng bo'lgan bildirishnomalarni ko'rsatadi.
        """
        qs = super().get_queryset(request)
        today = now().date()
        return qs.filter(date=today)
