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


class OrderingFilter(admin.SimpleListFilter):
    title = 'Ordering'
    parameter_name = 'ordering'

    def lookups(self, request, model_admin):
        orderings = StatementColumn.objects.order_by('ordering').values_list('ordering', flat=True).distinct()
        return [(ordering, ordering) for ordering in orderings if ordering]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(ordering=self.value())
        return queryset


@admin.register(StatementColumn)
class StatementColumnAdmin(AdminHistoryMixin, admin.ModelAdmin):
    form = StatementColumnAdminForm
    list_display = ('statement', 'title_uz', 'title_ru', 'ordering', 'parent', 'has_ordering', 'created_at')
    list_display_links = ("statement", "title_uz", "title_ru")
    search_fields = (
        'title_uz',
        'title_ru',
        'statement__name_uz',
        'statement__name_ru',
        'ordering',
    )
    list_filter = ('statement', OrderingFilter)
    ordering = ('ordering',)
    autocomplete_fields = ('statement', 'parent')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('statement', 'parent')

    def has_ordering(self, obj):
        return obj.ordering

    has_ordering.admin_order_field = 'ordering'
    has_ordering.short_description = "Ordering"
