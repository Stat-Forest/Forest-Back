from django.contrib import admin
from apps.reports.models import DashboardStat

@admin.register(DashboardStat)
class DashboardStatAdmin(admin.ModelAdmin):
    list_display = [
        'sent_reports',
        'returned_reports',
        'accepted_reports',
        'draft_reports',
        'responsible_users',
        'deadlines',
        'updated_at',
    ]
    readonly_fields = [
        'sent_reports',
        'returned_reports',
        'accepted_reports',
        'draft_reports',
        'responsible_users',
        'deadlines',
        'updated_at',
        'created_at',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
