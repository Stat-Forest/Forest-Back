from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from apps.reports.models import StatementColumn
from apps.logs.mixins import AdminHistoryMixin

class StatementColumnAdminForm(forms.ModelForm):
    class Meta:
        model = StatementColumn
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        statement = cleaned_data.get('statement')
        parent = cleaned_data.get('parent')

        # Validation: A column cannot be its own parent
        if parent and parent.id == self.instance.id:
            raise forms.ValidationError({
                'parent': _('A column cannot be its own parent.')
            })

        # Validation: parent must belong to the same statement
        if parent and parent.statement != statement:
            raise forms.ValidationError({
                'parent': _('The parent column must belong to the same statement.')
            })

        return cleaned_data


@admin.register(StatementColumn)
class StatementColumnAdmin(AdminHistoryMixin,admin.ModelAdmin):
    form = StatementColumnAdminForm
    list_display = ('statement', 'title_uz', 'title_ru', 'ordering', 'parent', 'created_at')
    search_fields = ('title', 'statement__name_uz', 'statement__name_ru', 'ordering')
    list_filter = ('statement', 'title_uz', 'title_ru')
    ordering = ('ordering',)
    raw_id_fields = ('statement', 'parent')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('statement', 'parent')
