from django.contrib import admin
from apps.reports.models import StatementColumn


@admin.register(StatementColumn)
class StatementColumnAdmin(admin.ModelAdmin):
    list_display = ('statement', 'title', 'ordering', 'created_at')
    search_fields = ('title', 'statement__name')
    list_filter = ('statement',)
    ordering = ('ordering',)
    raw_id_fields = ("statement", "parent")

    def get_queryset(self, request):
        query_set = super().get_queryset(request)
        return query_set.select_related("statement", "parent")

