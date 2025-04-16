from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import admin
from .report_form import ReportAdminForm
from ..models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    form = ReportAdminForm
    list_display = ('organization_display', 'statement', 'period', 'sent_at', 'submission_at')
    list_filter = ('status', 'period', 'statement')
    readonly_fields = ('sent_at', 'status',)
    search_fields = ('organization__name',)
    date_hierarchy = 'sent_at'
    ordering = ('-sent_at',)

    def organization_display(self, obj):
        orgs = obj.organization.all()
        org_names = "<br>".join([org.name for org in orgs])
        return format_html('<div style="max-height: 80px; overflow-y: auto; width: 150px;">{}</div>', mark_safe(org_names))
    organization_display.short_description = "Organizations"
