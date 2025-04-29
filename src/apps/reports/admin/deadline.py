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
                        _("Bu organizations, statement va submit_at kombinatsiyasi uchun deadline allaqachon mavjud.")
                    )

        if period == 'daily':
            # Sana formati YYYY-MM-DD bo'lishini tekshirish
            if len(submission_at) != 10 or submission_at[4] != '-' or submission_at[7] != '-':
                raise forms.ValidationError(_("Yaroqsiz sana formati. YYYY-MM-DD formatini ishlating"))

            year, month, day = submission_at.split('-')
            if not (year.isdigit() and len(year) == 4):
                raise forms.ValidationError(_("Yilni to'liq (4 raqam) kiriting."))
            if not (month.isdigit() and len(month) == 2 and 1 <= int(month) <= 12):
                raise forms.ValidationError(_("Oy 01 dan 12 gacha bo'lishi kerak."))
            if not (day.isdigit() and len(day) == 2 and 1 <= int(day) <= 31):
                raise forms.ValidationError(_("Kun 01 dan 31 gacha bo'lishi kerak."))

            try:
                datetime.strptime(submission_at, '%Y-%m-%d')
            except ValueError:
                raise forms.ValidationError(_("Yaroqsiz sana. YYYY-MM-DD formatini ishlating"))
        elif period == 'weekly':
            if len(submission_at) != 10 or not submission_at[:4].isdigit() or not submission_at[
                                                                                  5:7].isdigit() or \
                    submission_at[7] != '-' or not submission_at[8:].startswith('W'):
                raise forms.ValidationError(_("Yaroqsiz hafta formati. YYYY-MM-Wxx formatini ishlating"))
            try:
                datetime.strptime(submission_at, '%Y-%m-W%U')
            except ValueError:
                raise forms.ValidationError(_("Yaroqsiz hafta formati. YYYY-MM-Wxx formatini ishlating"))
        elif period == 'monthly':
            if len(submission_at) != 7 or not submission_at[:4].isdigit() or not submission_at[5:7].isdigit() or \
                    submission_at[4] != '-':
                raise forms.ValidationError(_("Yaroqsiz oy formati. YYYY-MM formatini ishlating"))
            try:
                datetime.strptime(submission_at, '%Y-%m')
            except ValueError:
                raise forms.ValidationError(_("Yaroqsiz oy formati. YYYY-MM formatini ishlating"))
        elif period == 'quarterly':
            if len(submission_at) != 7 or not submission_at[:4].isdigit() or not submission_at[6:7].isdigit() or \
                    submission_at[4] != '-' or not submission_at[5] =='Q' or submission_at[
                6] not in ['1', '2', '3', '4']:
                raise forms.ValidationError(_("Yaroqsiz chorak formati. YYYY-Qx formatini ishlating"))
        elif period == 'yearly':
            if len(submission_at) != 4 or not submission_at.isdigit():
                raise forms.ValidationError(_("Yaroqsiz yil formati. YYYY formatini ishlating"))
            try:
                datetime.strptime(submission_at, '%Y')
            except ValueError:
                raise forms.ValidationError(_("Yaroqsiz yil formati. YYYY formatini ishlating"))

        return cleaned_data



class DeadlineAdmin(admin.ModelAdmin):
    form = DeadlineAdminForm
    list_display = ('statement', 'submit_at', 'organizations_display')
    search_fields = ('statement__name', 'submit_at')

    def organizations_display(self, obj):
        return ", ".join([organization.name for organization in obj.organizations.all()])

    organizations_display.short_description = _("Tashkilotlar")


admin.site.register(Deadline, DeadlineAdmin)
