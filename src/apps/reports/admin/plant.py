from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from apps.reports.models import Plant


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ("id", "name_uz", "name_ru", "statement", "parent")
    list_filter = ("statement",)

    class Media:
        js = ("admin/js/plant_admin.js",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "load-parents/",
                self.admin_site.admin_view(self.load_parents),
                name="plant-load-parents",
            )
        ]
        return custom + urls

    def load_parents(self, request):
        statement_id = request.GET.get("statement")

        parents = (
            Plant.objects
            .filter(statement_id=statement_id, parent__isnull=True)
            .order_by("name")
        )

        return JsonResponse(
            [{"id": p.id, "name": p.name} for p in parents],
            safe=False
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent", "statement")