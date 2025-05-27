from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.users.models import CustomUser, PersonalInfo, Position


class PersonalInfoInline(admin.StackedInline):
    model = PersonalInfo
    fk_name = "user"
    extra = 0
    can_delete = False

    # bolim_admin da organizations bo`midi
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    model = CustomUser
    list_display = (
        "id", "email", "first_name", "last_name", "role", "gender", "is_active"
    )
    list_filter = (
        "role", "gender", "is_active", "is_disabled", "nationality", "is_superuser"
    )
    search_fields = (
        "email", "first_name", "last_name", "phone_number", "passport_number", "user_number"
    )
    ordering = ("-created_at",)
    readonly_fields = ("last_login", "created_at", "updated_at")

    fieldsets = (
        (_("Login Credentials"), {
            "fields": ("email", "password")
        }),
        (_("Personal Info"), {
            "fields": (
                "first_name", "last_name", "father_name", "gender", "date_of_birth",
                "date_of_place", "nationality", "passport_number", "phone_number", "address"
            )
        }),
        (_("Permissions and Role"), {
            "fields": (
                "role", "is_active", "is_staff", "is_superuser", "is_disabled", "groups", "user_permissions"
            )
        }),
        (_("Extra Info"), {
            "fields": ("user_number",
                       "statement",
                       "organization",
                       # "positions",
                       # "information",
                       # "name_of_education_university",
                       # "finished_of_education_university",
                       # "number_of_diploma",
                       # "specialization",
                       # "academic_of_degree",
                       # "temporary_job",
                       # "appointed_time",
                       # "completion_of_the_position_time",
                       # "languages",
                       # "countries_visited",
                       # "family_members",
                       # "party_membership",
                       # "deputy_member",
                       # "state_awards",
                       # "military_service",
                       # "convicted",
                       # "resume",
                       )
        }),
        (_("Important Dates"), {
            "fields": ("created_at", "updated_at")
        }),
    )

    add_fieldsets = (
        (_("Create User"), {
            "classes": ("wide",),
            "fields": (
                "email", "password1", "password2",
                "first_name", "last_name", "father_name",
                "gender", "nationality", "passport_number", "phone_number", "date_of_birth",
                "date_of_place", "address", "role", "user_number", "statement", "organization",
                "is_active", "is_staff", "is_superuser", "is_disabled", "groups", "user_permissions"
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("password") and not change:
            obj.set_password(form.cleaned_data["password"])
        elif "password" in form.changed_data:
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)

    inlines = [PersonalInfoInline]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    model = Position
    list_display = ("name", "slug")
    search_fields = ("name",)
