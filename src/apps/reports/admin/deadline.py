from django.contrib import admin
from apps.reports.models import Deadline


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ('statement', 'period', 'submit_at', 'get_organizations', 'created_at')
    list_filter = ('statement', 'period', 'submit_at')
    search_fields = ('statement',)
    filter_horizontal = ('organization',)

    def get_organizations(self, obj):
        return ", ".join([org.name for org in obj.organization.all()])
    get_organizations.short_description = 'Organizations'