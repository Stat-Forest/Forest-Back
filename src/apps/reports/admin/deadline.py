from datetime import datetime
from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from apps.reports.models import Deadline


class DeadlineAdminForm(forms.ModelForm):
    class Meta:
        model = Deadline
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        organizations = cleaned_data.get('organizations')
        statement = cleaned_data.get('statement')
        submission_at = self.cleaned_data.get('submit_at')
        period = statement.period

        if organizations and statement and submission_at:
            existing_deadlines = Deadline.objects.filter(statement=statement, submit_at=submission_at)
            for deadline in existing_deadlines:
                if set(deadline.organizations.all()) == set(organizations):
                    raise forms.ValidationError(
                        _("A deadline already exists for this combination of organizations, statement, and submit_at.")
                    )

        if period == 'daily':
            # Check that the date format is YYYY-MM-DD
            if len(submission_at) != 10 or submission_at[4] != '-' or not submission_at[4] !='-'  or submission_at[7] != '-':
                raise forms.ValidationError(_("Invalid date format. Please use the YYYY-MM-DD format"))

            year, month, day = submission_at.split('-')
            if not (year.isdigit() and len(year) == 4):
                raise forms.ValidationError(_("Please enter the year as a 4-digit number."))
            if not (month.isdigit() and len(month) == 2 and 1 <= int(month) <= 12):
                raise forms.ValidationError(_("Month should be between 01 and 12."))
            if not (day.isdigit() and len(day) == 2 and 1 <= int(day) <= 31):
                raise forms.ValidationError(_("Day should be between 01 and 31."))

            try:
                datetime.strptime(submission_at, '%Y-%m-%d')
            except ValueError:
                raise forms.ValidationError(_("Invalid date. Please use the YYYY-MM-DD format"))
        elif period == 'weekly':
            if len(submission_at) != 10 or not submission_at[:4].isdigit() or  not submission_at[4] !='-' or  not submission_at[
                                                                                  5:7].isdigit() or \
                    submission_at[7] != '-' or not submission_at[8:].startswith('W'):
                raise forms.ValidationError(_("Invalid week format. Please use the YYYY-MM-Wxx format"))
            try:
                datetime.strptime(submission_at, '%Y-%m-W%U')
            except ValueError:
                raise forms.ValidationError(_("Invalid week format. Please use the YYYY-MM-Wxx format"))
        elif period == 'monthly':
            if len(submission_at) != 7 or not submission_at[:4].isdigit() or not submission_at[4] !='-' or not submission_at[5:7].isdigit() or \
                    submission_at[4] != '-':
                raise forms.ValidationError(_("Invalid month format. Please use the YYYY-MM format"))
            try:
                datetime.strptime(submission_at, '%Y-%m')
            except ValueError:
                raise forms.ValidationError(_("Invalid month format. Please use the YYYY-MM format"))
        elif period == 'quarterly':
            if len(submission_at) != 7 or not submission_at[:4].isdigit() or not submission_at[4] !='-' or not submission_at[6:7].isdigit() or \
                    submission_at[4] != '-' or not submission_at[5] == 'Q' or submission_at[
                6] not in ['1', '2', '3', '4']:
                raise forms.ValidationError(_("Invalid quarter format. Please use the YYYY-Qx format"))
        elif period == 'yearly':
            if len(submission_at) != 4 or not submission_at.isdigit():
                raise forms.ValidationError(_("Invalid year format. Please use the YYYY format"))
            try:
                datetime.strptime(submission_at, '%Y')
            except ValueError:
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
