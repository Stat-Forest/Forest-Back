"""Yashil mahalla ma'lumotnomalari — asosiy stat admin saytida (`/admin/`)."""
from django.contrib import admin

from apps.base.admin import admin_site
from apps.yashil.models import (
    CalendarDay,
    CatalogItem,
    Mahalla,
    MahallaUnionRoute,
    NormRule,
    ObjectType,
    Season,
    ServiceCapacity,
    SupplierAssignment,
    SupplierProfile,
    UnionUnit,
    YashilMembership,
)


def register(model):
    def decorator(admin_class):
        admin_site.register(model, admin_class)
        return admin_class

    return decorator


class SupplierAssignmentInline(admin.TabularInline):
    model = SupplierAssignment
    extra = 0
    raw_id_fields = ("organization",)
    fields = ("organization", "valid_from", "valid_to", "source_doc")


class UnionRouteInline(admin.TabularInline):
    model = MahallaUnionRoute
    extra = 0
    fields = ("union_unit", "valid_from", "valid_to", "source_doc")


@register(Mahalla)
class MahallaAdmin(admin.ModelAdmin):
    list_display = ("name", "source_code", "district", "region", "is_active", "valid_from", "valid_to")
    list_filter = ("is_active", "region")
    search_fields = ("name", "source_code", "address")
    raw_id_fields = ("district",)
    inlines = (SupplierAssignmentInline, UnionRouteInline)
    list_select_related = ("district", "region")


@register(UnionUnit)
class UnionUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "region", "district", "is_active")
    list_filter = ("level", "is_active", "region")
    search_fields = ("name", "stir")
    raw_id_fields = ("district", "parent")


@register(MahallaUnionRoute)
class MahallaUnionRouteAdmin(admin.ModelAdmin):
    list_display = ("mahalla", "union_unit", "valid_from", "valid_to")
    list_filter = ("union_unit",)
    search_fields = ("mahalla__name", "mahalla__source_code")
    raw_id_fields = ("mahalla",)


@register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ("organization", "supplier_type", "parent", "is_active_supplier")
    list_filter = ("supplier_type", "is_active_supplier")
    search_fields = ("organization__name", "official_name", "stir")
    raw_id_fields = ("organization", "parent")
    filter_horizontal = ("service_regions", "service_districts")


@register(SupplierAssignment)
class SupplierAssignmentAdmin(admin.ModelAdmin):
    list_display = ("mahalla", "organization", "valid_from", "valid_to", "source_doc")
    list_filter = ("organization",)
    search_fields = ("mahalla__name", "mahalla__source_code", "organization__name")
    raw_id_fields = ("mahalla", "organization")


@register(YashilMembership)
class YashilMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "member_type", "cabinet_name", "can_prepare", "can_sign", "is_active", "valid_from", "valid_to")
    list_filter = ("member_type", "is_active", "can_sign")
    search_fields = ("user__email", "user__last_name", "user__first_name", "mahalla__name", "organization__name")
    raw_id_fields = ("user", "mahalla", "union_unit", "organization")
    fieldsets = (
        (None, {"fields": ("user", "member_type", "mahalla", "union_unit", "organization", "is_active", "valid_from", "valid_to")}),
        ("Vakolat", {"fields": ("can_prepare", "can_sign", "position_title", "phone",
                                 "authority_doc_number", "authority_doc_date", "authority_file")}),
        ("Kuzatuvchi ko'lami", {"fields": ("observer_scope",), "classes": ("collapse",)}),
    )


@register(CalendarDay)
class CalendarDayAdmin(admin.ModelAdmin):
    list_display = ("date", "kind", "note", "source_ref", "version")
    list_filter = ("kind",)
    date_hierarchy = "date"
    search_fields = ("note", "source_ref")


@register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("year", "kind", "date_from", "date_to", "is_active")
    list_filter = ("year", "kind")


@register(ObjectType)
class ObjectTypeAdmin(admin.ModelAdmin):
    list_display = ("order", "code", "name_cyr", "name_lat", "requires_note", "is_active")
    list_editable = ("requires_note", "is_active")
    ordering = ("order",)


@register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name_cyr", "supplier_type", "item_type", "category", "unit", "precision", "is_active", "version")
    list_filter = ("supplier_type", "item_type", "category", "is_active")
    search_fields = ("code", "name_cyr", "name_lat")
    readonly_fields = ("precision",)


@register(NormRule)
class NormRuleAdmin(admin.ModelAdmin):
    list_display = ("code", "version", "applies_to_category", "applies_to_item", "effective_from", "effective_to", "approved_ref")
    list_filter = ("applies_to_category",)
    search_fields = ("code", "description")
    raw_id_fields = ("applies_to_item",)


@register(ServiceCapacity)
class ServiceCapacityAdmin(admin.ModelAdmin):
    list_display = ("organization", "catalog_item", "period", "capacity")
    list_filter = ("period",)
    raw_id_fields = ("organization", "catalog_item")
