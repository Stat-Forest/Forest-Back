from django.contrib import admin
from apps.reports.models.plan import Plan, PlanItem


class PlanItemInline(admin.TabularInline):
    model = PlanItem
    extra = 1
    autocomplete_fields = ("column",)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "statement", "organization", "year", "created_at")
    list_filter = ("year", "organization", "statement")
    search_fields = ("organization__name_uz", "organization__name_ru", "statement__name")
    inlines = [PlanItemInline]


@admin.register(PlanItem)
class PlanItemAdmin(admin.ModelAdmin):
    list_display = ("id", "plan", "column", "plan_value", "created_at")
    list_filter = ("plan", "column")
    search_fields = ("plan__organization__name_uz", "plan__organization__name_ru", "column__name")
