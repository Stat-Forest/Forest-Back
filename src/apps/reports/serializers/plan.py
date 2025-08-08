from rest_framework import serializers
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Plan
from apps.utils.translation import get_lang_code, get_translated_field

from django.utils.translation import gettext_lazy as _

from apps.reports.models import Plan, Statement, StatementColumn
from apps.general.models import Organization
from apps.reports.models import Plan, PlanItem, Statement, StatementColumn



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
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Plan
        fields = [
            'id',
            'statement',
            'statement_name',
            'organization',
            'organization_name',
            'year',
            'plan_items',
            'created_at',
        ]

    def get_statement_name(self, obj):
        lang = self.context.get("lang", "uz")
        return getattr(obj.statement, f"name_{lang}", obj.statement.name_uz)

    def get_organization_name(self, obj):
        return obj.organization.name

    def get_plan_items(self, obj):
        lang = self.context.get("lang", "uz")
        return [
            {
                "column_id": item.column.id,
                "column_name": (
                                   f"{getattr(item.column.parent, f'title_{lang}', item.column.parent.title_uz)} — "
                                   if item.column.parent else ""
                               ) + getattr(item.column, f"title_{lang}", item.column.title_uz),
                "plan_value": item.plan_value,
            }
            for item in obj.plan_items.select_related("column", "column__parent").all()
        ]



class PlanItemValueUpdateSerializer(serializers.Serializer):
    column_id = serializers.UUIDField(write_only=True)
    value = serializers.IntegerField(min_value=0)
    column_name = serializers.SerializerMethodField(read_only=True)

    def validate(self, attrs):
        plan = self.context.get("plan")
        column_id = attrs.get("column_id")

        try:
            plan_item = PlanItem.objects.get(plan=plan, column_id=column_id)
        except PlanItem.DoesNotExist:
            raise serializers.ValidationError({
                "column_id": f"PlanItem with column {column_id} does not exist in this plan."
            })

        attrs["column"] = column_id  # internal use
        self._column_obj = plan_item.column
        return attrs

    def get_column_name(self, obj):
        column = getattr(self, "_column_obj", None)
        if column is None and hasattr(obj, "column"):
            column = obj.column
        if column:
            lang = get_lang_code(self.context)
            return get_translated_field(column, 'name', lang)
        return None


class PlanUpdateSerializer(serializers.Serializer):
    organization = serializers.UUIDField()
    year = serializers.IntegerField(min_value=1900)
    plan_items = PlanItemSerializer(many=True)

    def validate_year(self, value):
        from django.utils import timezone
        current_year = timezone.now().year
        if value < 2020 or value > current_year:
            raise CustomExceptionError(
                400,
                {'year': _('Year must be between 2024 and current year.')}
            )
        return value

    def validate(self, attrs):
        if not attrs.get('plan_items'):
            raise CustomExceptionError(400, {'plan_items': _('Plan items are required.')})
        return attrs

    def update(self, instance, validated_data):
        organization_id = validated_data.get("organization")
        year = validated_data.get("year")
        items = validated_data.get("plan_items", [])

        organization = Organization.objects.get(id=organization_id)

        if instance.organization != organization:
            instance.organization = organization

        instance.year = year
        instance.save()

        existing_items = {
            item.column_id: item for item in instance.plan_items.all()
        }
        incoming_column_ids = set()

        for item in items:
            column_id = item["column"]
            plan_value = item["plan_value"]
            incoming_column_ids.add(column_id)

            column = StatementColumn.objects.get(id=column_id)

            PlanItem.objects.update_or_create(
                plan=instance,
                column=column,
                defaults={"plan_value": plan_value}
            )

        for column_id, plan_item in existing_items.items():
            if column_id not in incoming_column_ids:
                plan_item.delete()

        return instance
