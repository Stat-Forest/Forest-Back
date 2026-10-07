from django.contrib import admin

from apps.base.admin import admin_site
from apps.billing.models import (
    ActivityType,
    Bolim,
    Contract,
    ContractAction,
    ContractActionProduct,
    ContractActivity,
    ContractFile,
    ContractHistory,
    ContractLand,
    ContractPrivilege,
    ContractYearlyAmount,
    District,
    LandType,
    PrivilegeType,
    Region,
    Renter,
    Xojalik,
    XojalikKontur,
    XojalikLocation,
)
from apps.logs.mixins import AdminHistoryMixin


def register(model):
    """Standart admin va loyihaning `admin_site`iga birdaniga ro'yxatdan o'tkazadi."""

    def decorator(admin_class):
        admin.site.register(model, admin_class)
        admin_site.register(model, admin_class)
        return admin_class

    return decorator


@register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "billing_id")
    search_fields = ("name", "code")
    ordering = ("name",)


@register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "region")
    list_filter = ("region",)
    search_fields = ("name", "code")


@register(Xojalik)
class XojalikAdmin(admin.ModelAdmin):
    list_display = ("name", "inn", "code", "region", "organization", "is_active")
    list_filter = ("region", "is_active")
    search_fields = ("name", "inn", "code")
    autocomplete_fields = ("organization",)


@register(Bolim)
class BolimAdmin(admin.ModelAdmin):
    list_display = ("name", "xojalik")
    list_filter = ("xojalik__region",)
    search_fields = ("name", "xojalik__name")


@register(Renter)
class RenterAdmin(admin.ModelAdmin):
    list_display = ("full_name", "pinfl", "stir", "phone", "is_legal_entity")
    list_filter = ("is_legal_entity",)
    search_fields = ("full_name", "pinfl", "stir", "passport", "phone")


class _TypeAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    search_fields = ("name",)
    list_filter = ("parent",)


@register(LandType)
class LandTypeAdmin(_TypeAdmin):
    pass


@register(ActivityType)
class ActivityTypeAdmin(_TypeAdmin):
    pass


@register(PrivilegeType)
class PrivilegeTypeAdmin(_TypeAdmin):
    list_display = ("name", "month", "parent")


class ContractYearlyAmountInline(admin.TabularInline):
    model = ContractYearlyAmount
    extra = 0


class ContractLandInline(admin.TabularInline):
    model = ContractLand
    extra = 0


class ContractActivityInline(admin.TabularInline):
    model = ContractActivity
    extra = 0


class ContractPrivilegeInline(admin.TabularInline):
    model = ContractPrivilege
    extra = 0


class ContractFileInline(admin.TabularInline):
    model = ContractFile
    extra = 0
    fields = ("file", "description", "uploaded_by", "created_at")
    readonly_fields = ("uploaded_by", "created_at")


@register(Contract)
class ContractAdmin(AdminHistoryMixin, admin.ModelAdmin):
    list_display = ("number", "contract_number", "xojalik", "renter", "status", "contract_date", "expired_date", "rent_amount", "paid_amount")
    list_filter = ("status", "xojalik__region", "contract_date")
    search_fields = ("number", "contract_number", "renter__full_name", "renter__pinfl", "renter__stir", "xojalik__name")
    date_hierarchy = "contract_date"
    autocomplete_fields = ("renter", "xojalik", "bolim", "region", "district")
    readonly_fields = ("number", "created_at", "updated_at", "created_by", "updated_by")
    inlines = (ContractYearlyAmountInline, ContractLandInline, ContractActivityInline, ContractPrivilegeInline, ContractFileInline)


class ContractActionProductInline(admin.TabularInline):
    model = ContractActionProduct
    extra = 0


@register(ContractAction)
class ContractActionAdmin(admin.ModelAdmin):
    list_display = ("contract", "vacancy", "own_investment")
    search_fields = ("contract__number", "contract__contract_number")
    autocomplete_fields = ("contract",)
    inlines = (ContractActionProductInline,)


@register(ContractYearlyAmount)
class ContractYearlyAmountAdmin(admin.ModelAdmin):
    list_display = ("contract", "year", "contract_amount", "calculated_amount", "paid_amount", "penalty_amount")
    list_filter = ("year",)
    search_fields = ("contract__number", "contract__contract_number")
    autocomplete_fields = ("contract",)


@register(ContractFile)
class ContractFileAdmin(AdminHistoryMixin, admin.ModelAdmin):
    list_display = ("contract", "file", "description", "uploaded_by", "created_at")
    search_fields = ("contract__number", "contract__contract_number", "description")
    autocomplete_fields = ("contract",)


@register(ContractHistory)
class ContractHistoryAdmin(admin.ModelAdmin):
    list_display = ("contract", "reason", "executor", "created_at")
    list_filter = ("reason",)
    search_fields = ("contract__number", "contract__contract_number")
    readonly_fields = ("contract", "executor", "reason", "data", "created_at")


class XojalikKonturInline(admin.TabularInline):
    model = XojalikKontur
    extra = 0
    fields = ("seq", "kontur_raqami", "area_ga")
    readonly_fields = ("seq", "kontur_raqami", "area_ga")
    can_delete = False
    max_num = 0


@register(XojalikLocation)
class XojalikLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "xojalik", "area_ga", "parcel_count")
    list_filter = ("region",)
    search_fields = ("name",)
    autocomplete_fields = ("xojalik",)
    exclude = ("boundary_geojson",)
    inlines = (XojalikKonturInline,)


@register(XojalikKontur)
class XojalikKonturAdmin(admin.ModelAdmin):
    list_display = ("xojalik_location", "kontur_raqami", "area_ga")
    list_filter = ("xojalik_location__region",)
    search_fields = ("kontur_raqami", "xojalik_location__name")
    exclude = ("geojson",)
