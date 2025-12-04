from collections import defaultdict
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.general.models import Organization
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Plan, PlanItem, Statement, StatementColumn
from apps.logs.models import HistoryActionJournal


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
QUARTERS = set(MONTHS_BY_QUARTER.keys())


class PlanItemSerializer(serializers.Serializer):
    column = serializers.UUIDField(write_only=True)
    column_id = serializers.SerializerMethodField()
    column_name = serializers.SerializerMethodField()
    column_parent_name = serializers.SerializerMethodField()
    plan_value = serializers.FloatField()

    def get_column_id(self, obj):
        return obj.column.id

    def get_column_name(self, obj):
        lang = self.context.get("lang", "uz")
        return getattr(obj.column, f"title_{lang}", obj.column.title)

    def get_column_parent_name(self, obj):
        lang = self.context.get("lang", "uz")
        names = []
        parent = getattr(obj.column, "parent", None)
        while parent:
            names.append(getattr(parent, f"title_{lang}", parent.title))
            parent = getattr(parent, "parent", None)
        return " - ".join(reversed(names)) if names else None


class PlanSerializer(serializers.ModelSerializer):
    plan_items = PlanItemSerializer(many=True)
    organization = serializers.UUIDField()
    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    statement_id = serializers.UUIDField(source="statement.id", read_only=True)
    statement = serializers.UUIDField(required=False)

    class Meta:
        model = Plan
        fields = ["id", "organization", "organization_id", "statement", "statement_id", "year", "plan_items"]
        read_only_fields = ["statement", "statement_id"]

    def validate_year(self, value):
        from django.utils import timezone
        current_year = timezone.now().year
        if value < 2024 or value > current_year:
            raise CustomExceptionError(
                400, {"year": _("Year must be between 2024 and current year.")}
            )
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("statement"):
            raise CustomExceptionError(
                400, {"statement": _("This field is required.")}
            )
        if not attrs.get("plan_items"):
            raise CustomExceptionError(
                400, {"plan_items": _("Plan items are required.")}
            )
        return attrs

    # ======================= PLAN ITEMS ================================

    def _save_plan_items(self, plan, statement, items):
        monthly_values = defaultdict(float)
        quarterly_values = defaultdict(float)
        yearly_values = defaultdict(float)
        yearly_columns = []
        yearly_total_col = None

        # 1️⃣ User yuborgan itemlarni joylashtirish
        for item in items:
            column = StatementColumn.objects.get(id=item["column"])
            value = item["plan_value"]

            if column.statement_id != statement.id:
                raise CustomExceptionError(
                    400,
                    {
                        "detail": f"Column {column.id} belongs to statement {column.statement_id}, "
                                  f"but you sent statement {statement.id}"
                    }
                )

            PlanItem.objects.update_or_create(
                plan=plan, column=column, defaults={"plan_value": value}
            )

            # Oylik / chorak / yil
            if column.status_plan in sum(MONTHS_BY_QUARTER.values(), []):
                monthly_values[column.status_plan] = value
            elif column.status_plan in QUARTERS:
                quarterly_values[column.status_plan] = value
            elif column.status_plan == StatementColumn.PlanStatus.YILLIK:
                yearly_values[column.id] = value
                yearly_columns.append(column)
            elif column.status_plan == StatementColumn.PlanStatus.YILLIK_TOTAL:
                yearly_total_col = column

        # 2️⃣ Oylik → chorak + yillik
        if monthly_values:
            for q_status, months in MONTHS_BY_QUARTER.items():
                total = sum(monthly_values[m] for m in months if m in monthly_values)
                if total > 0:
                    quarter_col = StatementColumn.objects.filter(
                        statement=statement, status_plan=q_status
                    ).first()
                    if quarter_col:
                        PlanItem.objects.update_or_create(
                            plan=plan, column=quarter_col, defaults={"plan_value": total}
                        )
                        quarterly_values[q_status] = total

            # choraklardan yillik
            if quarterly_values:
                total_yearly = sum(quarterly_values.values())
                for col in StatementColumn.objects.filter(
                        statement=statement,
                        status_plan=StatementColumn.PlanStatus.YILLIK
                ):
                    PlanItem.objects.update_or_create(
                        plan=plan, column=col, defaults={"plan_value": total_yearly}
                    )

        # 3️⃣ Chorak → yillik
        elif quarterly_values:
            total_yearly = sum(quarterly_values.values())
            for col in StatementColumn.objects.filter(
                    statement=statement,
                    status_plan=StatementColumn.PlanStatus.YILLIK
            ):
                PlanItem.objects.update_or_create(
                    plan=plan, column=col, defaults={"plan_value": total_yearly}
                )

        # 4️⃣ Yillik → yillik total
        elif yearly_values:
            total_value = sum(yearly_values.values())
            yearly_total_col = StatementColumn.objects.filter(
                statement=statement,
                status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL
            ).first()
            if yearly_total_col:
                PlanItem.objects.update_or_create(
                    plan=plan, column=yearly_total_col, defaults={"plan_value": total_value}
                )

    # ======================= CREATE ================================

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        organization = Organization.objects.get(id=validated_data["organization"])
        statement = Statement.objects.get(id=validated_data["statement"])
        year = validated_data["year"]
        items = validated_data["plan_items"]

        plan, created = Plan.objects.get_or_create(
            organization=organization, statement=statement, year=year
        )

        # log create
        HistoryActionJournal.objects.create(
            user=user,
            action='add',
            model_name='Plan',
            object_id=plan.id,
            object_repr=str(plan),
            change_message="Plan created" ,
        )

        self._save_plan_items(plan, statement, items)
        return plan

    # ======================= UPDATE ================================

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        validated_data.pop("statement", None)

        if "organization" in validated_data:
            instance.organization = Organization.objects.get(
                id=validated_data["organization"]
            )

        instance.year = validated_data.get("year", instance.year)


        items = validated_data.get("plan_items", [])
        self._save_plan_items(instance, instance.statement, items)
        return instance



class PlanListItemSerializer(serializers.ModelSerializer):
    column_id = serializers.UUIDField(source='column.id', read_only=True)
    column_parent_name = serializers.SerializerMethodField()
    column_name = serializers.SerializerMethodField()

    class Meta:
        model = PlanItem
        fields = ["column_id", "column_parent_name", "column_name", "plan_value"]

    def get_column_parent_name(self, obj):
        lang = self.context.get("lang", "uz")
        names = []
        parent = getattr(obj.column, "parent", None)
        while parent:
            names.append(getattr(parent, f"title_{lang}", parent.title))
            parent = getattr(parent, "parent", None)
        return " - ".join(reversed(names)) if names else None

    def get_column_name(self, obj):
        lang = self.context.get("lang", "uz")
        return getattr(obj.column, f"title_{lang}", obj.column.title)


from django.utils import timezone

class PlanListSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    statement = serializers.SerializerMethodField()
    plan_items = PlanListItemSerializer(many=True, read_only=True)
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = ("id", "year", "created_at", "updated_at", "organization", "statement", "plan_items")

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

    def get_updated_at(self, obj):
        dt = obj.updated_at or obj.created_at
        return timezone.localtime(dt).strftime("%d.%m.%Y %H:%M") if dt else None
