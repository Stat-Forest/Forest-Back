"""
Billing modellari faqat alohida `billing_admin_site`da (`/billing-admin/`) —
stat `admin_site` va standart `admin.site`da ro'yxatdan o'tkazilmaydi.
"""
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group
from django.db.models import Prefetch

from apps.billing.admin_site import billing_admin_site
from apps.billing.models import (
    BILLING_ROLES,
    ActivityType,
    BillingUser,
    BillingUserAccess,
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
    MibPushLog,
    PrivilegeType,
    Region,
    Renter,
    Xojalik,
    XojalikKontur,
    XojalikLocation,
)
from apps.billing.services import mib_push
from apps.logs.mixins import AdminHistoryMixin


def register(model):
    """Faqat billing adminkasida ro'yxatdan o'tkazadi."""

    def decorator(admin_class):
        billing_admin_site.register(model, admin_class)
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
    list_select_related = ("region", "organization")


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

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        mib_push.schedule_contract_push(form.instance.id)


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


# ---------------------------------------------------------------------------
# Billing foydalanuvchilari (proxy CustomUser: billing_user / billing_super)
# ---------------------------------------------------------------------------
ROLE_CHOICES = [(role.value, role.label) for role in BILLING_ROLES]


def _xojaliklar_field():
    return forms.ModelMultipleChoiceField(
        label="Biriktirilgan xo'jaliklar",
        queryset=Xojalik.objects.select_related("region").order_by("name"),
        required=False,
        widget=FilteredSelectMultiple("Xo'jaliklar", is_stacked=False),
        help_text="billing_user faqat shu xo'jaliklar doirasida ko'radi va yozadi; billing_super uchun ahamiyatsiz.",
    )


class _BillingUserFormMixin:
    def _init_billing_fields(self):
        self.fields["role"].choices = ROLE_CHOICES
        if "organization" in self.fields:
            self.fields["organization"].required = False
        if self.instance and self.instance.pk:
            access = BillingUserAccess.objects.filter(user_id=self.instance.pk).first()
            self.fields["xojaliklar"].initial = list(access.xojaliklar.values_list("pk", flat=True)) if access else []

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        qs = BillingUser.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Bu elektron pochta bilan foydalanuvchi allaqachon mavjud.")
        return email


class BillingUserCreationForm(_BillingUserFormMixin, BaseUserCreationForm):
    """Yaratish: email, ism, familiya, parol x2 (set_password), rol, xo'jaliklar, tashkilot, faol."""

    role = forms.ChoiceField(label="Rol", choices=ROLE_CHOICES, initial=ROLE_CHOICES[0][0])
    xojaliklar = _xojaliklar_field()

    class Meta:
        model = BillingUser
        fields = ("email", "first_name", "last_name", "role", "organization", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_billing_fields()


class BillingUserChangeForm(_BillingUserFormMixin, UserChangeForm):
    """Tahrir: parol maydoni yo'q (faqat o'qiladi) — "Parolni o'zgartirish" havolasi orqali."""

    role = forms.ChoiceField(label="Rol", choices=ROLE_CHOICES)
    xojaliklar = _xojaliklar_field()

    class Meta:
        model = BillingUser
        fields = ("email", "password", "first_name", "last_name", "role", "organization", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_billing_fields()


@register(BillingUser)
class BillingUserAdmin(UserAdmin):
    form = BillingUserChangeForm
    add_form = BillingUserCreationForm
    list_display = ("email", "first_name", "last_name", "role", "organization", "xojaliklar_list", "is_active", "last_login")
    list_filter = ("role", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    filter_horizontal = ()
    readonly_fields = ("last_login", "created_at")
    list_select_related = ("organization",)
    fieldsets = (
        ("Kirish", {"fields": ("email", "password")}),
        ("Shaxsiy ma'lumot", {"fields": ("first_name", "last_name")}),
        ("Rol va doira", {"fields": ("role", "xojaliklar", "organization", "is_active")}),
        ("Sanalar", {"fields": ("last_login", "created_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "first_name", "last_name", "password1", "password2",
                "role", "xojaliklar", "organization", "is_active",
            ),
        }),
    )

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .filter(role__in=[role.value for role in BILLING_ROLES])
            .prefetch_related(Prefetch("billing_access__xojaliklar", queryset=Xojalik.objects.only("id", "name")))
        )

    @admin.display(description="Xo'jaliklar")
    def xojaliklar_list(self, obj):
        access = getattr(obj, "billing_access", None)
        if obj.role == BILLING_ROLES[1]:
            return "Barchasi"
        names = [x.name for x in access.xojaliklar.all()] if access else []
        return ", ".join(names) or "—"

    def save_model(self, request, obj, form, change):
        obj.is_staff = False
        obj.is_superuser = False
        super().save_model(request, obj, form, change)
        group, _ = Group.objects.get_or_create(name=obj.role)
        obj.groups.set([group])

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        access, _ = BillingUserAccess.objects.get_or_create(
            user_id=form.instance.pk, defaults={"created_by": request.user, "updated_by": request.user},
        )
        access.xojaliklar.set(form.cleaned_data.get("xojaliklar") or [])


@register(MibPushLog)
class MibPushLogAdmin(admin.ModelAdmin):
    list_display = ("contract_number", "status", "attempts", "http_status", "sent_at", "created_at")
    list_filter = ("status",)
    search_fields = ("contract_number", "correlation_id")
    readonly_fields = [f.name for f in MibPushLog._meta.fields]
    actions = ("resend",)

    def get_fields(self, request, obj=None):
        # payload (ijarachi pasport/JSHSHIR/telefon) faqat superuser'ga ko'rinadi (audit M1/F5)
        fields = super().get_fields(request, obj)
        if request.user.is_superuser:
            return fields
        return [f for f in fields if f not in ("payload", "response")]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.action(description="Shartnomaning joriy holatini MIB'ga qayta yuborish")
    def resend(self, request, queryset):
        if not request.user.is_superuser:
            # Ruxsatsiz amallar Django'da faqat ko'rish huquqi bilan ham ishlaydi
            self.message_user(request, "Faqat superuser qayta yubora oladi", level=messages.ERROR)
            return
        contract_ids = {log.contract_id for log in queryset if log.contract_id}
        for contract_id in contract_ids:
            mib_push.push_contract(contract_id, force=True)
        self.message_user(request, f"{len(contract_ids)} ta shartnoma qayta yuborildi")
