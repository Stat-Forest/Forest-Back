from django.contrib import admin
from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'from_time', 'to_time', 'ordering', 'is_active')
    list_filter = ('from_time', 'to_time')
    search_fields = ('title', 'desc')
    ordering = ('ordering',)
    readonly_fields = ('is_active',)

    def is_active(self, obj):
        from django.utils import timezone
        now = timezone.now()
        return obj.from_time <= now <= obj.to_time
    is_active.boolean = True
    is_active.short_description = "Active Now?"
