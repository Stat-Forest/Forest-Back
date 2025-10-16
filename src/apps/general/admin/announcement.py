from django.contrib import admin
from django.utils import timezone
from apps.general.models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title_uz', 'title_ru','desc_uz', 'desc_ru', 'from_time', 'to_time', 'ordering', 'is_active_now')
    list_filter = ('from_time', 'to_time')
    search_fields = ('title_uz', 'title_ru', 'desc_uz', 'desc_ru')
    ordering = ('ordering',)

    def is_active_now(self, obj):
        """
        Hozirgi vaqtda e'lon faol yoki yo'qligini aniqlaydi.
        """
        now = timezone.now()
        return obj.from_time <= now <= obj.to_time

    is_active_now.boolean = True
    is_active_now.short_description = "Faolmi?"
