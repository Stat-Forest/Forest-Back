from django.contrib import admin
from .models import ReportItem, ReportItemInner


class ReportItemInnerInline(admin.TabularInline):
    model = ReportItemInner
    extra = 1
    fields = ("value", "created_at")
    readonly_fields = ("created_at",)


@admin.register(ReportItem)
class ReportItemAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "plant", "statement_column", "short_value", "created_at")
    list_filter = ("report", "plant", "statement_column")
    search_fields = (
        "report__id",
        "plant__name",
        "statement_column__name",
        "value",
    )
    inlines = [ReportItemInnerInline]

    def short_value(self, obj):
        return (obj.value[:50] + "...") if obj.value and len(obj.value) > 50 else obj.value
    short_value.short_description = "Value"


@admin.register(ReportItemInner)
class ReportItemInnerAdmin(admin.ModelAdmin):
    list_display = ("id", "report_item", "short_value", "created_at")
    list_filter = ("report_item",)
    search_fields = ("value",)

    def short_value(self, obj):
        return (obj.value[:50] + "...") if obj.value and len(obj.value) > 50 else obj.value
    short_value.short_description = "Value"
