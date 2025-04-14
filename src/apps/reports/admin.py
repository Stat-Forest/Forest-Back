from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('organization', 'statement', 'period', 'sent_at', 'submission_at')
    list_filter = ('status', 'period', 'statement')
    readonly_fields = ('sent_at', 'submission_at','status')
    search_fields = ('organization__name',)
    date_hierarchy = 'sent_at'
    ordering = ('-sent_at',)

