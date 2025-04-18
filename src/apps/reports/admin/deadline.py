from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import admin
from .deadline_form import DeadlineAdminForm
from ..models import Deadline


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    form = DeadlineAdminForm
    list_display = ('organization_display', 'statement', 'period','submission_at',)
    list_filter = ('period', 'statement')
    search_fields = ('organization__name',)

    def organization_display(self, obj):
        orgs = obj.organization.all()
        org_names = "<br>".join([org.name for org in orgs])
        return format_html('<div style="max-height: 80px; overflow-y: auto; width: 150px;">{}</div>', mark_safe(org_names))
    organization_display.short_description = "Organizations"
