from django.contrib import admin

from apps.reports.models import Plant, ColumnPlant


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ("id", "name_uz", "name_ru", "statement", "parent")
    list_display_links = list_display
    list_filter = ("name_uz", "name_ru", "statement", "statement__parent")

    def get_queryset(self, request):
        query_set = super().get_queryset(request)
        return query_set.select_related("parent", "statement")