from rest_framework import serializers

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Plan
from apps.utils.translation import get_lang_code, get_translated_field

from django.utils.translation import gettext_lazy as _

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            'id',
            'statement',
            'organization',
            'column',
            'year',
            'plan_value'
        ]

    def validate_year(self, value):
        from django.utils import timezone

        current_year = timezone.now().year
        if value < 1900 or value > current_year:
            raise CustomExceptionError(
                400,
                {'year': _('Year must be between 1900 and current year.')}
            )
        return value

    def validate_plan_value(self, value):
        if value < 0:
            raise CustomExceptionError(
                400,
                {'plan_value': _('Plan value cannot be negative.')}
            )
        return value


class PlanListSerializer(serializers.ModelSerializer):
    statement_name = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    column_title = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            'id',
            'statement',
            'statement_name',
            'organization',
            'organization_name',
            'column',
            'column_title',
            'year',
            'plan_value'
        ]

    def get_lang(self):
        return get_lang_code(self.context)

    def get_statement_name(self, obj):
        return get_translated_field(obj.statement, 'name', self.get_lang())

    def get_organization_name(self, obj):
        return get_translated_field(obj.organization, 'name', self.get_lang())

    def get_column_title(self, obj):
        return get_translated_field(obj.column, 'title', self.get_lang())