from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.reports.models import Statement
from apps.logs.mixins import AdminHistoryMixin


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


@admin.register(Statement)
class StatementAdmin(AdminHistoryMixin, admin.ModelAdmin):
    form = StatementAdminForm
    list_display = ('name_uz', 'name_ru', 'period', 'parent','is_used')
    list_filter = ("name_uz", "name_ru",'is_used')
    search_fields = ("name_uz", "name_ru", "period", "parent")

    def get_queryset(self, request):
        query_set = super().get_queryset(request)
        return query_set.select_related("parent")
