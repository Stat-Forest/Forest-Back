from collections import defaultdict

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from apps.general.models import Organization
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Plan, PlanItem, Statement, StatementColumn
from apps.utils.translation import get_lang_code, get_translated_field


MONTHS_BY_QUARTER = {
    'CHORAK_1': ['YANVAR', 'FEVRAL', 'MART'],
    'CHORAK_2': ['APREL', 'MAY', 'IYUN'],
    'CHORAK_3': ['IYUL', 'AVGUST', 'SENTABR'],
    'CHORAK_4': ['OKTABR', 'NOYABR', 'DEKABR'],
}

QUARTERS = ['CHORAK_1', 'CHORAK_2', 'CHORAK_3', 'CHORAK_4']

# === Konstantalar ===
MONTHS_BY_QUARTER = {
    StatementColumn.PlanStatus.CHORAK_1: [
        StatementColumn.PlanStatus.YANVAR,
        StatementColumn.PlanStatus.FEVRAL,
        StatementColumn.PlanStatus.MART,
    ],
    StatementColumn.PlanStatus.CHORAK_2: [
        StatementColumn.PlanStatus.APREL,
        StatementColumn.PlanStatus.MAY,
        StatementColumn.PlanStatus.IYUN,
    ],
    StatementColumn.PlanStatus.CHORAK_3: [
        StatementColumn.PlanStatus.IYUL,
        StatementColumn.PlanStatus.AVGUST,
        StatementColumn.PlanStatus.SENTABR,
    ],
    StatementColumn.PlanStatus.CHORAK_4: [
        StatementColumn.PlanStatus.OKTABR,
        StatementColumn.PlanStatus.NOYABR,
        StatementColumn.PlanStatus.DEKABR,
    ],
}

QUARTERS = {
    StatementColumn.PlanStatus.CHORAK_1,
    StatementColumn.PlanStatus.CHORAK_2,
    StatementColumn.PlanStatus.CHORAK_3,
    StatementColumn.PlanStatus.CHORAK_4,
}


class PlanItemSerializer(serializers.Serializer):
    column = serializers.UUIDField(source="column_id")
    column_name = serializers.SerializerMethodField()
    plan_value = serializers.FloatField()

    def get_column_name(self, obj):
        lang = self.context.get("lang", "uz")
        if lang == "ru":
            return getattr(obj.column, "title_ru", obj.column.title)
        return getattr(obj.column, "title_uz", obj.column.title)

class PlanSerializer(serializers.ModelSerializer):
    plan_items = PlanItemSerializer(many=True)
    organization = serializers.UUIDField()
    statement = serializers.UUIDField() 

    class Meta:
        model = Plan
        fields = ["id", "organization", "statement", "year", "plan_items"]
        read_only_fields = ["statement"]

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

    def _save_plan_items(self, plan, statement, items):
        """ PlanItem larni yaratish / update qilish logikasi """
        monthly_values = defaultdict(int)
        quarterly_values = defaultdict(int)

        for item in items:
            column = StatementColumn.objects.get(id=item["column"])
            value = item["plan_value"]

            if column.statement_id != statement.id:
                raise CustomExceptionError(
                    400,
                    _("Column does not belong to the given statement")
                )

            PlanItem.objects.update_or_create(
                plan=plan,
                column=column,
                defaults={"plan_value": value}
            )

            if column.status_plan in sum(MONTHS_BY_QUARTER.values(), []):
                monthly_values[column.status_plan] += value
            elif column.status_plan in QUARTERS:
                quarterly_values[column.status_plan] += value
            elif column.status_plan == StatementColumn.PlanStatus.YILLIK:
                total_col = StatementColumn.objects.filter(
                    statement=statement,
                    status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL
                ).first()
                if total_col:
                    PlanItem.objects.update_or_create(
                        plan=plan,
                        column=total_col,
                        defaults={"plan_value": value}
                    )

        # Oyliklardan choraklarni hisoblash
        if monthly_values:
            for q_status, months in MONTHS_BY_QUARTER.items():
                total = sum(monthly_values[m] for m in months if m in monthly_values)
                if total > 0:
                    quarter_col = StatementColumn.objects.filter(
                        statement=statement, status_plan=q_status
                    ).first()
                    if quarter_col:
                        PlanItem.objects.update_or_create(
                            plan=plan,
                            column=quarter_col,
                            defaults={"plan_value": total}
                        )
                        quarterly_values[q_status] += total

        # Choraklardan yillik va totalni hisoblash
        if quarterly_values:
            yearly_total = sum(quarterly_values.values())

            yearly_col = StatementColumn.objects.filter(
                statement=statement,
                status_plan=StatementColumn.PlanStatus.YILLIK
            ).first()
            if yearly_col:
                PlanItem.objects.update_or_create(
                    plan=plan,
                    column=yearly_col,
                    defaults={"plan_value": yearly_total}
                )

            total_col = StatementColumn.objects.filter(
                statement=statement,
                status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL
            ).first()
            if total_col:
                PlanItem.objects.update_or_create(
                    plan=plan,
                    column=total_col,
                    defaults={"plan_value": yearly_total}
                )

    @transaction.atomic
    def create(self, validated_data):
        organization = Organization.objects.get(id=validated_data["organization"])
        statement = Statement.objects.get(id=validated_data["statement"])
        year = validated_data["year"]
        items = validated_data["plan_items"]

        plan, _ = Plan.objects.get_or_create(
            organization=organization,
            statement=statement,
            year=year
        )
        self._save_plan_items(plan, statement, items)
        return plan

    @transaction.atomic
    def update(self, instance, validated_data):
        # statement update bo‘lmaydi
        if "organization" in validated_data:
            instance.organization = Organization.objects.get(id=validated_data["organization"])
        instance.year = validated_data.get("year", instance.year)
        instance.save()

        items = validated_data.get("plan_items", [])
        self._save_plan_items(instance, instance.statement, items)
        return instance

class PlanListSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    statement = serializers.SerializerMethodField()
    plan_items = PlanItemSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = ("id", "year", "organization", "statement", "plan_items")

    def get_organization(self, obj):
        lang = self.context.get("lang", "uz")
        if lang == "ru":
            return getattr(obj.organization, "name_ru", obj.organization.name)
        return getattr(obj.organization, "name_uz", obj.organization.name)

    def get_statement(self, obj):
        lang = self.context.get("lang", "uz")
        if lang == "ru":
            return getattr(obj.statement, "name_ru", obj.statement.name)
        return getattr(obj.statement, "name_uz", obj.statement.name)


