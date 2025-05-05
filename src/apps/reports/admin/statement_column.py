from django.contrib import admin
from apps.reports.models import StatementColumn

@admin.register(StatementColumn)
class StatementColumnAdmin(admin.ModelAdmin):
    list_display = ('statement', 'title', 'plane','is_only_plane','ordering','created_at')
    search_fields = ('title', 'statement__name')
    list_filter = ('statement',)
    ordering = ('ordering',)
