from datetime import datetime, timedelta
import re

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.admin import DateFieldListFilter
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe

from apps.general.models import Organization
from apps.reports.models import Deadline
from apps.logs.mixins import AdminHistoryMixin


# ================================
# Validators
# ================================
def validate_deadline_at(value):
    """
    DD/MM/YYYY format validatsiyasi
    """
    if isinstance(value, str):
        try:
            datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            raise forms.ValidationError(
                _("Deadline date must be in DD/MM/YYYY format")
            )


# ================================
# Admin Form
# ================================
class DeadlineAdminForm(forms.ModelForm):
    organizations = forms.ModelMultipleChoiceField(
        queryset=Organization.objects.all().order_by("name"),
        required=True,
        widget=FilteredSelectMultiple(
            verbose_name=_("Organizations"),
            is_stacked=False,
            attrs={"style": "height: 350px; width: 350px;"},
        ),
    )

    class Media:
        css = {
            "all": ("admin/css/widgets.css",)
        }
        js = (
            "admin/js/core.js",
            "admin/js/SelectFilter2.js",
        )

    class Meta:
        model = Deadline
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        organizations = cleaned_data.get("organizations")
        statement = cleaned_data.get("statement")
        submit_at = cleaned_data.get("submit_at")
        deadline_at = cleaned_data.get("deadline_at")
        period = statement.period if statement else None

        # --- deadline_at format ---
        if deadline_at:
            validate_deadline_at(deadline_at)

        # --- duplicate check ---
        if organizations and statement and submit_at:
            qs = Deadline.objects.filter(
                statement=statement,
                submit_at=submit_at,
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            for obj in qs:
                if set(obj.organizations.all()) == set(organizations):
                    raise forms.ValidationError(
                        _(
                            "A deadline already exists for this combination of "
                            "organizations, statement, and submit_at."
                        )
                    )

        # --- submit_at format validation ---
        if period == "daily":
            # 1️⃣ qat'iy format: YYYY-MM-DD
            pattern = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"
            if not re.match(pattern, submit_at):
                raise forms.ValidationError(
                    _("Invalid date format. Use YYYY-MM-DD (e.g. 2025-01-01)")
                )

            # 2️⃣ real sana ekanini tekshirish (masalan 2025-02-30 bo‘lmasligi kerak)
            try:
                datetime.strptime(submit_at, "%Y-%m-%d")
            except ValueError:
                raise forms.ValidationError(
                    _("Invalid calendar date.")
                )

        elif period == "weekly":
            if not re.match(r"^\d{4}-\d{2}-HAFTALIK_[1-4]$", submit_at):
                raise forms.ValidationError(
                    _("Invalid week format. Use: YYYY-MM-HAFTALIK_x")
                )


        elif period == "monthly":

            pattern = r"^\d{4}_(0[1-9]|1[0-2])$"

            if not re.match(pattern, submit_at):
                raise forms.ValidationError(

                    _("Invalid month format. Use YYYY_MM (e.g. 2025_01, 2025_12)")

                )

        elif period == "quarterly":
            if not re.match(r"^\d{4}-CHORAK_[1-4]$", submit_at):
                raise forms.ValidationError(
                    _("Invalid quarter format. Use: YYYY-CHORAK_x")
                )

        elif period == "yearly":
            if not submit_at.isdigit() or len(submit_at) != 4:
                raise forms.ValidationError(
                    _("Invalid year format. Use YYYY")
                )

        return cleaned_data


# ================================
# Deadline date filter (custom)
# ================================
class DeadlineDateFilter(admin.SimpleListFilter):
    title = _("Deadline date")
    parameter_name = "deadline_at"

    def lookups(self, request, model_admin):
        return (
            ("today", _("Today")),
            ("past_7", _("Last 7 days")),
            ("this_month", _("This month")),
            ("this_year", _("This year")),
        )

    def queryset(self, request, queryset):
        today = datetime.today().date()

        if self.value() == "today":
            return queryset.filter(deadline_at=today)

        if self.value() == "past_7":
            return queryset.filter(
                deadline_at__gte=today - timedelta(days=7),
                deadline_at__lte=today,
            )

        if self.value() == "this_month":
            return queryset.filter(
                deadline_at__year=today.year,
                deadline_at__month=today.month,
            )

        if self.value() == "this_year":
            return queryset.filter(deadline_at__year=today.year)

        return queryset


# ================================
# Deadline Admin
# ================================
@admin.register(Deadline)
class DeadlineAdmin(AdminHistoryMixin, admin.ModelAdmin):
    form = DeadlineAdminForm

    list_display = (
        "statement",
        "statement_period",
        "submit_at",
        "deadline_at_display",
        "organizations_display",
        "created_at",
    )

    list_filter = (
        "statement",
        "submit_at",
        DeadlineDateFilter,
        ("created_at", DateFieldListFilter),  # ✅ created_at filter
    )

    search_fields = (
        "statement__name",
        "submit_at",
    )

    ordering = ("-created_at",)

    # ----------------------------
    # Custom columns
    # ----------------------------
    def statement_period(self, obj):
        return obj.statement.period if obj.statement else "-"

    statement_period.short_description = _("Period")

    def deadline_at_display(self, obj):
        return obj.deadline_at.strftime("%d/%m/%Y") if obj.deadline_at else "-"

    deadline_at_display.short_description = _("Deadline date")

    def organizations_display(self, obj):
        orgs = obj.organizations.all().order_by("name")

        items = "".join(f"<li>{org.name}</li>" for org in orgs)

        return mark_safe(
            f"""
            <div style="
                max-height:150px;
                overflow-y:auto;
                border:1px solid #ddd;
                padding:6px;
                background:#fafafa;
                border-radius:4px;
            ">
                <ul style="margin:0;padding-left:18px;">
                    {items}
                </ul>
            </div>
            """
        )

    organizations_display.short_description = _("Organizations")
