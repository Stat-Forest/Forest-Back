from datetime import datetime
import re
from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from apps.general.models import Organization
from apps.reports.models import Deadline
from apps.logs.mixins import AdminHistoryMixin
from django.utils.safestring import mark_safe


def validate_deadline_at(value):
    """DD/MM/YYYY format validatsiyasi"""
    if isinstance(value, str):
        try:
            datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            raise forms.ValidationError(_("Deadline date must be in DD/MM/YYYY format"))


class DeadlineAdminForm(forms.ModelForm):
    organizations = forms.ModelMultipleChoiceField(
        queryset=Organization.objects.all().order_by('name'),
        required=True,
        widget=FilteredSelectMultiple(
            verbose_name=_("Organizations"),
            is_stacked=False,
            attrs={
                "style": "height: 350px; width: 350px;"  # scroll + chiroyli ko‘rinish
            }
        )
    )

    class Media:
        css = {
            "all": (
                "admin/css/widgets.css",   # SelectFilter uchun kerak
            )
        }
        js = (
            "admin/js/core.js",
            "admin/js/SelectFilter2.js",   # asosiy JS (bunsiz ishlamaydi)
        )

    class Meta:
        model = Deadline
        fields = "__all__"

    def clean_organizations(self):
        return self.cleaned_data["organizations"]

    def clean(self):
        cleaned_data = super().clean()

        organizations = cleaned_data.get("organizations")
        statement = cleaned_data.get("statement")
        submission_at = cleaned_data.get("submit_at")
        deadline_at = cleaned_data.get("deadline_at")
        period = statement.period if statement else None

        # --- deadline_at format ---
        if deadline_at:
            validate_deadline_at(deadline_at)

        # --- duplicate check ---
        if organizations and statement and submission_at:
            existing = Deadline.objects.filter(
                statement=statement,
                submit_at=submission_at
            )
            for d in existing:
                if set(d.organizations.all()) == set(organizations):
                    raise forms.ValidationError(
                        _("A deadline already exists for this combination of organizations, statement, and submit_at.")
                    )

        # --- submit_at formatlar ---
        if period == "daily":
            try:
                datetime.strptime(submission_at, "%Y-%m-%d")
            except ValueError:
                raise forms.ValidationError(_("Invalid date format. Please use YYYY-MM-DD"))

        elif period == "weekly":
            pattern = r"^\d{4}-\d{2}-HAFTALIK_[1-4]$"
            if not re.match(pattern, submission_at):
                raise forms.ValidationError(_("Invalid week format. Use: YYYY-MM-HAFTALIK_x"))

        elif period == "monthly":
            try:
                datetime.strptime(submission_at, "%Y-%m")
            except ValueError:
                raise forms.ValidationError(_("Invalid month format. Use: YYYY-MM"))

        elif period == "quarterly":
            pattern = r"^\d{4}-CHORAK_[1-4]$"
            if not re.match(pattern, submission_at):
                raise forms.ValidationError(_("Invalid quarter format. Use: YYYY-CHORAK_x"))

        elif period == "yearly":
            if not submission_at.isdigit() or len(submission_at) != 4:
                raise forms.ValidationError(_("Invalid year format. Use: YYYY"))

        return cleaned_data


# ================================
# Custom Date Filter
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

        elif self.value() == "past_7":
            from datetime import timedelta
            start = today - timedelta(days=7)
            return queryset.filter(deadline_at__gte=start, deadline_at__lt=today)

        elif self.value() == "this_month":
            return queryset.filter(deadline_at__year=today.year, deadline_at__month=today.month)

        elif self.value() == "this_year":
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
        "statement__period",
        "submit_at",
        "deadline_at_display",
        "organizations_display",
    )

    list_filter = (
        "statement",
        "submit_at",
        DeadlineDateFilter,
    )

    search_fields = ("statement__name", "submit_at", "deadline_at")

    def organizations_display(self, obj):
        orgs = obj.organizations.all().order_by("name")

        html_list = "<ul style='margin:0; padding-left:16px;'>"
        for org in orgs:
            html_list += f"<li>{org.name}</li>"
        html_list += "</ul>"

        # scroll beramiz
        return mark_safe(
            f"""
            <div style="
                max-height: 150px;
                overflow-y: auto;
                border: 1px solid #ddd;
                padding: 4px 8px;
                background: #fafafa;
                border-radius: 4px;
            ">
                {html_list}
            </div>
            """
        )

    organizations_display.short_description = _("Organizations")

    def deadline_at_display(self, obj):
        return obj.deadline_at.strftime("%d/%m/%Y") if obj.deadline_at else "-"

    deadline_at_display.short_description = _("Deadline date")
