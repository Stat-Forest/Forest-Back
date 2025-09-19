from datetime import datetime
import re
from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.general.models import Organization
from apps.reports.models import Deadline


class DeadlineAdminForm(forms.ModelForm):
    organizations = forms.MultipleChoiceField(
        required=True,
    )

    class Meta:
        model = Deadline
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Organizations queryset
        qs = Organization.objects.all()

        # Sun’iy ALL variantini qo‘shamiz
        choices = [("ALL", "All organizations")] + [(org.id, org.name) for org in qs]
        self.fields['organizations'].choices = choices

    def clean_organizations(self):
        data = self.cleaned_data['organizations']

        if "ALL" in data:
            # Agar ALL tanlansa → barcha organization id-larni qaytaramiz
            return Organization.objects.all()
        else:
            # Oddiy holatda faqat tanlangan id-lar
            return Organization.objects.filter(id__in=data)

    def clean(self):
        cleaned_data = super().clean()
        organizations = cleaned_data.get('organizations')
        statement = cleaned_data.get('statement')
        submission_at = cleaned_data.get('submit_at')
        period = statement.period if statement else None

        if organizations and "ALL" in [org.name for org in organizations]:
            cleaned_data['organizations'] = Organization.objects.all()

        if organizations and statement and submission_at:
            existing_deadlines = Deadline.objects.filter(statement=statement, submit_at=submission_at)
            for deadline in existing_deadlines:
                if set(deadline.organizations.all()) == set(organizations):
                    raise forms.ValidationError(
                        _("A deadline already exists for this combination of organizations, statement, and submit_at.")
                    )

        # === DAILY ===
        if period == 'daily':
            try:
                datetime.strptime(submission_at, '%Y-%m-%d')
            except ValueError:
                raise forms.ValidationError(_("Invalid date format. Please use the YYYY-MM-DD format"))

        # === WEEKLY ===
        elif period == 'weekly':
            # Kutilyotgan format: YYYY-MM-HAFTALIK_x (x=1..4)
            pattern = r'^\d{4}-\d{2}-HAFTALIK_[1-4]$'
            if not re.match(pattern, submission_at):
                raise forms.ValidationError(_("Invalid week format. Please use the YYYY-MM-HAFTALIK_x format"))

        # === MONTHLY ===
        elif period == 'monthly':
            try:
                datetime.strptime(submission_at, '%Y-%m')
            except ValueError:
                raise forms.ValidationError(_("Invalid month format. Please use the YYYY-MM format"))

        # === QUARTERLY ===
        elif period == 'quarterly':
            # Kutilyotgan format: YYYY-CHORAK_x (x=1..4)
            pattern = r'^\d{4}-CHORAK_[1-4]$'
            if not re.match(pattern, submission_at):
                raise forms.ValidationError(_("Invalid quarter format. Please use the YYYY-CHORAK_x format"))

        # === YEARLY ===
        elif period == 'yearly':
            if not submission_at.isdigit() or len(submission_at) != 4:
                raise forms.ValidationError(_("Invalid year format. Please use the YYYY format"))

        return cleaned_data


class DeadlineAdmin(admin.ModelAdmin):
    form = DeadlineAdminForm
    list_display = ('statement','statement__period', 'submit_at', 'organizations_display')
    search_fields = ('statement__name', 'submit_at')

    def organizations_display(self, obj):
        return ", ".join([organization.name for organization in obj.organizations.all()])

    organizations_display.short_description = _("Organizations")


admin.site.register(Deadline, DeadlineAdmin)
