from django.contrib import admin
from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'organization',
        'statement',
        "is_general",
        "is_individual_general",
        "is_report",
        "is_republic",
        'deadline',
        'status',
        'created_at',
    )
    list_filter = ('status', 'organization', 'statement', 'deadline')
    search_fields = ('organization__name', 'statement__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('organization', 'statement', 'deadline', 'is_report', 'status', 'cancel_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        query_set = super().get_queryset(request)
        return query_set.select_related("statement", "organization", "deadline", "republic")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True
