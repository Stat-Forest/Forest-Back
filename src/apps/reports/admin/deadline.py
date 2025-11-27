from datetime import datetime
import re
from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.general.models import Organization
from apps.reports.models import Deadline
from apps.logs.mixins import AdminHistoryMixin


def validate_deadline_at(value):
    """
    DD/MM/YYYY format validatsiyasi
    """
    try:
        datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        raise forms.ValidationError(_("Deadline date must be in DD/MM/YYYY format"))


class DeadlineAdminForm(forms.ModelForm):
    organizations = forms.MultipleChoiceField(required=True)

    class Meta:
        model = Deadline
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Organization.objects.all()
        choices = [("ALL", "All organizations")] + [(org.id, org.name) for org in qs]

        self.fields['organizations'].choices = choices

    def clean_organizations(self):
        data = self.cleaned_data['organizations']

        if "ALL" in data:
            return Organization.objects.all()

        return Organization.objects.filter(id__in=data)

    def clean(self):
        cleaned_data = super().clean()

        organizations = cleaned_data.get('organizations')
        statement = cleaned_data.get('statement')
        submission_at = cleaned_data.get('submit_at')
        deadline_at = cleaned_data.get('deadline_at')
        period = statement.period if statement else None

        # --- deadline_at validatsiyasi ---
        if deadline_at:
            validate_deadline_at(deadline_at)

        # ALL tanlangan bo‘lsa
        if organizations and "ALL" in [org.name for org in organizations]:
            cleaned_data['organizations'] = Organization.objects.all()

        # Duplicate check
        if organizations and statement and submission_at:
            existing_deadlines = Deadline.objects.filter(
                statement=statement,
                submit_at=submission_at
            )
            for deadline in existing_deadlines:
                if set(deadline.organizations.all()) == set(organizations):
                    raise forms.ValidationError(
                        _("A deadline already exists for this combination of organizations, statement, and submit_at.")
                    )

        # submit_at format validation
        if period == 'daily':
            try:
                datetime.strptime(submission_at, '%Y-%m-%d')
            except ValueError:
                raise forms.ValidationError(_("Invalid date format. Please use the YYYY-MM-DD format"))

        elif period == 'weekly':
            pattern = r'^\d{4}-\d{2}-HAFTALIK_[1-4]$'
            if not re.match(pattern, submission_at):
                raise forms.ValidationError(_("Invalid week format. Please use the YYYY-MM-HAFTALIK_x format"))

        elif period == 'monthly':
            try:
                datetime.strptime(submission_at, '%Y-%m')
            except ValueError:
                raise forms.ValidationError(_("Invalid month format. Please use the YYYY-MM format"))

        elif period == 'quarterly':
            pattern = r'^\d{4}-CHORAK_[1-4]$'
            if not re.match(pattern, submission_at):
                raise forms.ValidationError(_("Invalid quarter format. Please use the YYYY-CHORAK_x format"))

        elif period == 'yearly':
            if not submission_at.isdigit() or len(submission_at) != 4:
                raise forms.ValidationError(_("Invalid year format. Please use the YYYY format"))

        return cleaned_data


# --------------------------------------------------------------------------------------------


@admin.register(Deadline)
class DeadlineAdmin(AdminHistoryMixin, admin.ModelAdmin):
    form = DeadlineAdminForm

    list_display = (
        'statement',
        'statement__period',
        'submit_at',
        'deadline_at',
        'organizations_display'
    )

    search_fields = ('statement__name', 'submit_at', 'deadline_at')

    def organizations_display(self, obj):
        return ", ".join(
            [organization.name for organization in obj.organizations.all()]
        )

    organizations_display.short_description = _("Organizations")
