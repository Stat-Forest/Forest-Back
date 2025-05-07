from django.contrib import admin

from apps.users.models import CustomUser, PersonalInfo, Position


class PersonalInfoInline(admin.StackedInline):
    model = PersonalInfo
    extra = 0
    can_delete = False
    verbose_name_plural = "Personal Information"
    fk_name = "user"

    # bolim_admin da organizations bo`midi
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "statement",
        "role",
        "gender",
        "nationality",
        "is_disabled",
        "first_name",
        "last_name",
        "father_name",
        "email",
        "phone_number",
        "passport_number",
        "date_of_birth",
        "date_of_place",
        "address",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name", "phone_number")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {
            "fields": (
                "first_name", "last_name", "father_name", "phone_number",
                "passport_number", "date_of_birth", "date_of_place",
                "address", "gender", "nationality", "statement", "organizations",
            )
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")
        }),
        ("Role information", {"fields": ("role", "is_disabled")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "password1", "password2", "role", "gender", "nationality"),
        }),
    )

    inlines = (PersonalInfoInline,)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    model = Position
    list_display = ("name", "slug")
    search_fields = ("name",)
