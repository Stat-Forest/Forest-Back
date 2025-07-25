from rest_framework import serializers

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Plan
from apps.utils.translation import get_lang_code, get_translated_field

from django.utils.translation import gettext_lazy as _

from apps.reports.models import Plan, Statement, StatementColumn
from apps.general.models import Organization
from apps.reports.models import PlanItem


class PlanItemSerializer(serializers.Serializer):
    column = serializers.UUIDField()
    value = serializers.IntegerField(min_value=0, source='plan_value')

    def validate_value(self, value):
        if value < 0:
            raise CustomExceptionError(
                400,
                {'value': _('Plan value cannot be negative.')}
            )
        return value


class PlanSerializer(serializers.Serializer):
    organization = serializers.UUIDField()
    statement = serializers.UUIDField()
    year = serializers.IntegerField(min_value=1900)
    plan_items = PlanItemSerializer(many=True)

    def validate_year(self, value):
        from django.utils import timezone
        current_year = timezone.now().year
        if value < 2024 or value > current_year:
            raise CustomExceptionError(
                400,
                {'year': _('Year must be between 2024 and current year.')}
            )
        return value

    def validate(self, attrs):
        if not attrs.get('plan_items'):
            raise CustomExceptionError(400, {'plan_items': _('Plan items are required.')})
        return attrs

    def create(self, validated_data):
        organization_id = validated_data["organization"]
        statement_id = validated_data["statement"]
        year = validated_data["year"]
        items = validated_data["plan_items"]

        organization = Organization.objects.get(id=organization_id)
        statement = Statement.objects.get(id=statement_id)

        plan, _ = Plan.objects.get_or_create(
            organization=organization,
            statement=statement,
            year=year
        )



        for item in items:
            column = StatementColumn.objects.get(id=item["column"])
            value = item["plan_value"]

            if column.statement_id != statement.id:
                raise CustomExceptionError(400, _("Column does not belong to the given statement"))

            PlanItem.objects.update_or_create(
                plan=plan,
                column=column,
                defaults={"plan_value": value}
            )

        return plan


class PlanListSerializer(serializers.ModelSerializer):
    statement_name = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    plan_items = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            'id',
            'statement',
            'statement_name',
            'organization',
            'organization_name',
            'year',
            'plan_items'
        ]

    def get_lang(self):
        return get_lang_code(self.context)

    def get_statement_name(self, obj):
        return get_translated_field(obj.statement, 'name', self.get_lang())

    def get_organization_name(self, obj):
        return get_translated_field(obj.organization, 'name', self.get_lang())

    def get_plan_items(self, obj):
        plan_items = obj.plan_items.all()  # Fetch related PlanItem objects
        serializer = PlanItemSerializer(plan_items, many=True)
        return serializer.data



class PlanItemValueUpdateSerializer(serializers.Serializer):
    column = serializers.UUIDField()
    value = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        plan = self.context.get("plan")
        column = attrs.get("column")

        if not PlanItem.objects.filter(plan=plan, column_id=column).exists():
            raise serializers.ValidationError(f"PlanItem with column {column} does not exist in this plan.")
        return attrs

