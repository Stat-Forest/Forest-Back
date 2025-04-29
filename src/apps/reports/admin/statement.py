from django import forms
from django.contrib import admin
from apps.reports.models import Statement
from django.utils.translation import gettext_lazy as _


class StatementAdminForm(forms.ModelForm):
    class Meta:
        model = Statement
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        period = cleaned_data.get('period')

        if parent is None and period is not None:
            raise forms.ValidationError({
                'parent': _('Agar parent ko\'rsatilmagan bo\'lsa, period ham bo\'sh bo\'lishi kerak.')
            })
        return cleaned_data


class StatementAdmin(admin.ModelAdmin):
    form = StatementAdminForm
    list_display = ('name', 'period', 'parent')

admin.site.register(Statement, StatementAdmin)
