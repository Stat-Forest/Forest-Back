from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import CustomUser, PersonalInfo, Position


class PersonalInfoInline(admin.StackedInline):
    model = PersonalInfo
    extra = 0
    can_delete = False
    verbose_name_plural = "Personal Information"
    fk_name = "user"


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    inlines = (PersonalInfoInline,)
    list_display = ("email", "first_name", "last_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name", "phone_number")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "father_name", "phone_number", "passport_number",
                                      "date_of_birth", "date_of_place", "address", "gender", "nationality")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Role information", {"fields": ("role", "is_disabled")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "password1", "password2", "role", "gender", "nationality"),
        }),
    )


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    model = Position
    list_display = ("name", "slug")
    search_fields = ("name",)
