# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.users.models import CustomUser, PersonalInfo
from apps.logs.mixins import AdminHistoryMixin
from apps.users.admin_forms import CustomUserAdminForm

class PersonalInfoInline(admin.StackedInline):
    model = PersonalInfo
    fk_name = "user"
    extra = 0
    can_delete = False

@admin.register(CustomUser)
class CustomUserAdmin(AdminHistoryMixin, admin.ModelAdmin):
    model = CustomUser
    form = CustomUserAdminForm
    inlines = [PersonalInfoInline]
    filter_horizontal = ("region_user_orgs",)

    list_display = (
        "id", "email", "organization", "statement",
        "first_name", "last_name", "role", "gender", "is_active"
    )
    list_filter = ("role", "organization", "statement", "region")
    search_fields = (
        "email", "first_name", "last_name",
        "phone_number", "passport_number", "jshshr", "user_number"
    )
    ordering = ("-created_at",)
    readonly_fields = ("last_login", "created_at", "updated_at", "user_number")

    fieldsets = (
        (_("Login Credentials"), {"fields": ("email", "password")}),
        (_("Personal Info"), {
            "fields": (
                "first_name", "last_name", "father_name",
                "gender", "user_number", "statement",
                "organization", "date_of_birth", "date_of_place",
                "nationality", "passport_number", "jshshr",
                "phone_number", "address"
            )
        }),
        (_("Hududiy boshqarma"), {"fields": ("region", "region_user_orgs")}),
        (_("Permissions and Role"), {
            "fields": (
                "role", "is_active", "is_staff",
                "is_superuser", "is_disabled",
                "groups", "user_permissions"
            )
        }),
        (_("Important Dates"), {"fields": ("created_at", "updated_at")}),
    )

    add_fieldsets = (
        (_("Create User"), {
            "classes": ("wide",),
            "fields": (
                "email", "password1", "password2",
                "first_name", "last_name", "father_name",
                "gender", "nationality", "passport_number", "phone_number",
                "date_of_birth", "date_of_place", "address",
                "role", "statement", "organization",
                "region", "region_user_orgs",
                "is_active", "is_staff", "is_superuser",
                "is_disabled", "groups", "user_permissions"
            ),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("organization", "statement")

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("password") and not change:
            obj.set_password(form.cleaned_data["password"])
        elif "password" in form.changed_data:
            obj.set_password(obj.password)

        super().save_model(request, obj, form, change)

        # Rolga mos guruhni yangilash
        role_group_map = {
            CustomUser.Role.SUPER_ADMIN: "super_admin",
            CustomUser.Role.RAHBARIYAT: "rahbariyat",
            CustomUser.Role.BOLIM_ADMIN: "bolim_admin",
            CustomUser.Role.TASHKILOT_RAHBARI: "tashkilot_rahbari",
            CustomUser.Role.TASHKILOT_HODIMI: "tashkilot_hodimi",
            CustomUser.Role.HUDUDIY_BOSHQARMA: "hududiy_boshqarma",
        }
        group_name = role_group_map.get(obj.role)
        if group_name:
            try:
                group = Group.objects.get(name=group_name)
                obj.groups.set([group])
            except Group.DoesNotExist:
                print(f"Group {group_name} not found!")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance

        # Faqat HUDUDIY_BOSHQARMA uchun tekshiruv
        if obj.role != CustomUser.Role.HUDUDIY_BOSHQARMA:
            return

        if not obj.region:
            raise ValidationError("Hududiy boshqarma uchun region majburiy")

        orgs = obj.region_user_orgs.all()
        if not orgs.exists():
            raise ValidationError("Kamida bitta tashkilot biriktirilishi shart")

        invalid_orgs = orgs.exclude(region=obj.region)
        if invalid_orgs.exists():
            raise ValidationError(
                "Biriktirilgan tashkilotlar foydalanuvchi regioniga mos emas"
            )

        # Rol o‘zgarganda eski M2M va regionni tozalash
        if change:
            old_role = (
                CustomUser.objects
                .filter(pk=obj.pk)
                .values_list("role", flat=True)
                .first()
            )
            if old_role == CustomUser.Role.HUDUDIY_BOSHQARMA and obj.role != CustomUser.Role.HUDUDIY_BOSHQARMA:
                obj.region = None
                obj.region_user_orgs.clear()
                obj.save(update_fields=["region"])

# Groupni admin dan chiqarish
admin.site.unregister(Group)
