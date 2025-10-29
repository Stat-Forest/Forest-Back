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
                'parent': _('If no parent is specified, the period should also be empty.')
            })
        return cleaned_data


class StatementAdmin(admin.ModelAdmin):
    form = StatementAdminForm
    list_display = ('name_uz', 'name_ru', 'period', 'parent')
    list_filter = ("name_uz", "name_ru")
    search_fields = ("name_uz", "name_ru", "period", "parent")

    def get_queryset(self, request):
        query_set = super().get_queryset(request)
        return query_set.select_related("parent")

admin.site.register(Statement, StatementAdmin)
