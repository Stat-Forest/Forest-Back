from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from apps.reports.models import Plant


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ("name_uz", "name_ru", "statement", "parent", "children_count", "is_leaf")
    list_filter = ("statement",)
    search_fields = ("name", "name_uz", "name_ru")
    list_select_related = ("parent", "statement")
    list_per_page = 50
    ordering = ("statement", "parent__name", "name")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("statement", "parent", "name", "name_uz", "name_ru"),
            "description": (
                "⚠️ <b>MUHIM:</b> Yangi o'simlik qo'shishda avval <b>Statement</b> ni tanlang, "
                "keyin <b>Parent</b> ro'yxatidan tegishli kategoriyani tanlang. "
                "Agar parent tanlamasangiz, bu o'simlik <b>yangi kategoriya</b> (root) sifatida yaratiladi."
            ),
        }),
        ("Texnik ma'lumotlar", {
            "classes": ("collapse",),
            "fields": ("id", "created_at", "updated_at"),
        }),
    )

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
        """AJAX endpoint: tanlangan statementga tegishli root plantlarni qaytaradi."""
        statement_id = request.GET.get("statement")

        parents = (
            Plant.objects
            .filter(statement_id=statement_id, parent__isnull=True)
            .order_by("name")
        )

        return JsonResponse(
            [{"id": str(p.id), "name": p.name_uz or p.name} for p in parents],
            safe=False
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Parent FK uchun queryset ni cheklaymiz:
        - Add sahifasida: bo'sh queryset (JS AJAX orqali yuklaydi)
        - Change sahifasida: faqat shu statementga tegishli root plantlar
        """
        if db_field.name == "parent":
            # Change sahifasida: URL dan object_id ni olamiz
            # /admin/reports/plant/<uuid>/change/
            path_parts = request.path.strip("/").split("/")
            obj_id = None
            if "change" in path_parts:
                change_idx = path_parts.index("change")
                if change_idx > 0:
                    obj_id = path_parts[change_idx - 1]

            if obj_id:
                try:
                    plant = Plant.objects.get(pk=obj_id)
                    # Faqat shu statementga tegishli root plantlar
                    kwargs["queryset"] = Plant.objects.filter(
                        statement=plant.statement,
                        parent__isnull=True,
                    ).order_by("name")
                except Plant.DoesNotExist:
                    kwargs["queryset"] = Plant.objects.filter(
                        parent__isnull=True
                    ).order_by("name")
            else:
                # Add sahifasida: barcha root plantlar (server-side validation
                # uchun). JS UI da faqat tanlangan statement uchun ko'rsatadi.
                kwargs["queryset"] = Plant.objects.filter(
                    parent__isnull=True
                ).order_by("name")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("parent", "statement")
        qs = qs.prefetch_related("children")
        return qs

    def children_count(self, obj):
        """O'simlik ostidagi bolalar soni."""
        return obj.children.count()
    children_count.short_description = "Bolalar soni"

    def is_leaf(self, obj):
        """Leaf (yaproq) — bolasi yo'q o'simlik."""
        return obj.children.count() == 0
    is_leaf.short_description = "Leaf?"
    is_leaf.boolean = True