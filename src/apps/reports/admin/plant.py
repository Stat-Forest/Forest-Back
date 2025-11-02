from django.contrib import admin

from apps.reports.models import Plant


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ("name_uz", "name_ru", "statement", "parent")
    list_display_links = list_display

    def get_queryset(self, request):
        query_set = super().get_queryset(request)
        return query_set.select_related("parent", "statement")