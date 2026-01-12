from collections import defaultdict
from django.db import transaction, IntegrityError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.utils import timezone

from apps.general.models import Organization
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Plan, PlanItem, Statement, StatementColumn
from apps.logs.models import HistoryActionJournal

from decimal import Decimal
from apps.reports.models import Plant, PlantPlan, PlantPlanItem

class PlantPlanItemSerializer(serializers.Serializer):
    column = serializers.UUIDField()
    plan_value = serializers.DecimalField(max_digits=30, decimal_places=2)


class PlantPlanSerializer(serializers.Serializer):
    plant = serializers.UUIDField()
    items = PlantPlanItemSerializer(many=True)

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
    # INPUT
    column = serializers.UUIDField(write_only=True)

    # OUTPUT
    column_id = serializers.SerializerMethodField()
    column_name = serializers.SerializerMethodField()
    column_parent_name = serializers.SerializerMethodField()
    plan_value = serializers.FloatField()

    def get_column_id(self, obj):
        # obj.column allaqachon select_related bilan yuklangan
        return obj.column_id

    def get_column_name(self, obj):
        lang = self.context.get("lang", "uz")
        column = obj.column
        return getattr(column, f"title_{lang}", column.title)

    def get_column_parent_name(self, obj):
        lang = self.context.get("lang", "uz")
        names = []

        parent = obj.column.parent
        if parent:
            names.append(getattr(parent, f"title_{lang}", parent.title))
            if parent.parent:
                names.append(getattr(parent.parent, f"title_{lang}", parent.parent.title))

        return " - ".join(reversed(names)) if names else None


class PlantPlanItemOutSerializer(serializers.ModelSerializer):
    column_id = serializers.UUIDField(source="column.id")
    plan_value = serializers.DecimalField(max_digits=30, decimal_places=2)

    class Meta:
        model = PlantPlanItem
        fields = ("column_id", "plan_value")


class PlantPlanOutSerializer(serializers.ModelSerializer):
    plant = serializers.UUIDField(source="plant.id")
    items = PlantPlanItemOutSerializer(many=True)

    class Meta:
        model = PlantPlan
        fields = ("plant", "items")

class PlantPlanInSerializer(serializers.Serializer):
    plant = serializers.UUIDField()
    items = PlantPlanItemSerializer(many=True)


class PlanSerializer(serializers.ModelSerializer):
    # 🔹 INPUT
    plants = PlantPlanInSerializer(
        many=True,
        write_only=True,
        required=False
    )

    plan_items = PlanItemSerializer(many=True, required=False)

    # 🔹 OUTPUT
    plant_plans = PlantPlanOutSerializer(
        many=True,
        read_only=True
    )

    organization = serializers.UUIDField()
    statement = serializers.UUIDField(required=False)

    class Meta:
        model = Plan
        fields = [
            "id",
            "organization",
            "statement",
            "year",
            "season",
            "plants",
            "plant_plans",
            "plan_items",
        ]

    def validate(self, attrs):
        is_create = self.instance is None

        # ================= CREATE =================
        if is_create:
            statement_id = attrs.get("statement")
            organization_id = attrs.get("organization")
            year = attrs.get("year")

            if not statement_id:
                raise CustomExceptionError(400, {"statement": _("This field is required.")})
            if not organization_id:
                raise CustomExceptionError(400, {"organization": _("This field is required.")})
            if not year:
                raise CustomExceptionError(400, {"year": _("This field is required.")})

            statement = Statement.objects.filter(id=statement_id).first()
            if not statement:
                raise CustomExceptionError(400, {"statement": _("Invalid statement.")})

        # ================= UPDATE =================
        else:
            # UPDATE paytida statement DB dan olinadi
            statement = self.instance.statement

        plan_items = attrs.get("plan_items") or []
        plants = attrs.get("plants") or []

        # ===== CASE 1: PlantPlan =====
        if statement.use_plant_plan:
            if not plants:
                raise CustomExceptionError(
                    400, {"plants": _("Plants are required for this statement")}
                )
            if plan_items:
                raise CustomExceptionError(
                    400, {"plan_items": _("This statement does not accept plan_items")}
                )

        # ===== CASE 2: Normal Plan =====
        else:
            if not plan_items:
                raise CustomExceptionError(
                    400, {"plan_items": _("Plan items are required")}
                )
            if plants:
                raise CustomExceptionError(
                    400, {"plants": _("Plants are not allowed for this statement")}
                )

        return attrs

    def _save_plan_items(self, plan, statement, items):
        monthly_values = defaultdict(float)
        quarterly_values = defaultdict(float)
        yearly_values = defaultdict(float)
        yearly_columns = []
        yearly_total_col = None

        # NEW — For YILLIK_1,2,3 logic
        yil_values = {
            "y1": 0.0,
            "y2": 0.0,
            "y3_col": None,
        }

        # 1) Save incoming items and collect values
        if not items:
            return

        columns = {
            c.id: c
            for c in StatementColumn.objects.filter(
                id__in=[i["column"] for i in items]
            )
        }

        for item in items:
            column = columns.get(item["column"])
            if not column:
                raise CustomExceptionError(
                    400,
                    {"column": _("Invalid column")}
                )

            value = float(item["plan_value"]) if item["plan_value"] is not None else 0.0

            if column.statement_id != statement.id:
                raise CustomExceptionError(
                    400,
                    {
                        "detail": (
                            f"Column {column.id} belongs to statement {column.statement_id}, "
                            f"but you sent statement {statement.id}"
                        )
                    }
                )

            # create/update the PlanItem for the incoming one
            PlanItem.objects.update_or_create(
                plan=plan, column=column, defaults={"plan_value": value}
            )

            # collect by status
            status = column.status_plan

            # MONTHLY
            if status in sum(MONTHS_BY_QUARTER.values(), []):
                monthly_values[status] = value

            # QUARTER
            elif status in QUARTERS:
                quarterly_values[status] = value

            # OLD YEARLY (status = 'yillik')
            elif status == StatementColumn.PlanStatus.YILLIK:
                yearly_values[column.id] = value
                yearly_columns.append(column)

            # OLD YEARLY_TOTAL
            elif status == StatementColumn.PlanStatus.YILLIK_TOTAL:
                yearly_total_col = column

            # NEW YILLIK_1, YILLIK_2, YILLIK_3
            elif status == StatementColumn.PlanStatus.YILLIK_1:
                yil_values["y1"] = value
            elif status == StatementColumn.PlanStatus.YILLIK_2:
                yil_values["y2"] = value
            elif status == StatementColumn.PlanStatus.YILLIK_3:
                yil_values["y3_col"] = column

        # If YILLIK_3 column not provided in items, try to find it on statement (we still may need to create PlanItem)
        if yil_values["y3_col"] is None:
            yil_values["y3_col"] = StatementColumn.objects.filter(
                statement=statement,
                status_plan=StatementColumn.PlanStatus.YILLIK_3
            ).first()

        # Ensure we have reference to YILLIK_TOTAL column (if not provided in items)
        if yearly_total_col is None:
            yearly_total_col = StatementColumn.objects.filter(
                statement=statement,
                status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL
            ).first()

        # 2) If we have Y1 or Y2 values and Y3 column exists -> create/update YILLIK_3 PlanItem
        #    (Y3 is always sum of Y1 + Y2 regardless of other yearly values)
        if yil_values["y3_col"] and (yil_values["y1"] != 0.0 or yil_values["y2"] != 0.0):
            total_y3 = yil_values["y1"] + yil_values["y2"]
            PlanItem.objects.update_or_create(
                plan=plan,
                column=yil_values["y3_col"],
                defaults={"plan_value": total_y3}
            )

        # 3) OLD aggregation logic: MONTHLY -> QUARTER -> YEARLY (unchanged)
        # MONTHLY -> QUARTER
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

            # QUARTER -> YEARLY
            if quarterly_values:
                total_yearly = sum(quarterly_values.values())
                for col in StatementColumn.objects.filter(
                        statement=statement, status_plan=StatementColumn.PlanStatus.YILLIK
                ):
                    PlanItem.objects.update_or_create(
                        plan=plan, column=col, defaults={"plan_value": total_yearly}
                    )
                    yearly_values[col.id] = total_yearly

        # QUARTER -> YEARLY (only quarter sent)
        elif quarterly_values:
            total_yearly = sum(quarterly_values.values())
            for col in StatementColumn.objects.filter(
                    statement=statement, status_plan=StatementColumn.PlanStatus.YILLIK
            ):
                PlanItem.objects.update_or_create(
                    plan=plan, column=col, defaults={"plan_value": total_yearly}
                )
                yearly_values[col.id] = total_yearly

        # 4) NOW compute YILLIK_TOTAL
        # yearly_values currently contains values for columns with status_plan == 'yillik'
        # We must add Y1 + Y2 to this sum, but NOT include Y3.
        total_from_yearly_cols = sum(yearly_values.values()) if yearly_values else 0.0
        total_for_yearly_total = total_from_yearly_cols + yil_values["y1"] + yil_values["y2"]

        if yearly_total_col:
            PlanItem.objects.update_or_create(
                plan=plan,
                column=yearly_total_col,
                defaults={"plan_value": total_for_yearly_total}
            )

    def _save_plant_plan(self, plan, statement, plants_data):
        from apps.reports.models import Plant, PlantPlan, PlantPlanItem

        MONTH_STATUSES = sum(MONTHS_BY_QUARTER.values(), [])
        QUARTERS = set(MONTHS_BY_QUARTER.keys())

        # 1️⃣ Columns (3 query max)
        month_columns = {
            c.id: c
            for c in StatementColumn.objects.filter(
                statement=statement,
                status_plan__in=MONTH_STATUSES,
            )
        }

        quarter_columns = {
            c.status_plan: c
            for c in StatementColumn.objects.filter(
                statement=statement,
                status_plan__in=QUARTERS,
            )
        }

        yearly_column = StatementColumn.objects.filter(
            statement=statement,
            status_plan=StatementColumn.PlanStatus.YILLIK,
        ).first()

        # 2️⃣ Plants (1 query)
        plant_ids = [p["plant"] for p in plants_data]
        plants = {p.id: p for p in Plant.objects.filter(id__in=plant_ids)}

        # 3️⃣ PlantPlans (1 query)
        plant_plans = {
            pp.plant_id: pp
            for pp in PlantPlan.objects.filter(plan=plan, plant_id__in=plant_ids)
        }

        new_items = []
        update_items = []

        for plant_data in plants_data:
            plant = plants.get(plant_data["plant"])
            if not plant:
                raise CustomExceptionError(400, {"plant": _("Invalid plant")})

            plant_plan = plant_plans.get(plant.id)
            if not plant_plan:
                plant_plan = PlantPlan.objects.create(plan=plan, plant=plant)
                plant_plans[plant.id] = plant_plan

            items = plant_data.get("items", [])

            # 4️⃣ OLD ITEMS (1 query per plant)
            existing_items = {
                i.column_id: i
                for i in PlantPlanItem.objects.filter(plant_plan=plant_plan)
            }

            monthly_totals = defaultdict(Decimal)
            quarterly_totals = {}

            # ===== MONTHLY =====
            for item in items:
                column = month_columns.get(item["column"])
                if not column:
                    raise CustomExceptionError(
                        400, {"detail": _("Only monthly columns are allowed")}
                    )

                value = Decimal(item.get("plan_value") or 0)
                monthly_totals[column.status_plan] += value

                obj = existing_items.get(column.id)
                if obj:
                    obj.plan_value = value
                    update_items.append(obj)
                else:
                    new_items.append(
                        PlantPlanItem(
                            plant_plan=plant_plan,
                            column=column,
                            plan_value=value,
                        )
                    )

            # ===== QUARTER =====
            for q_status, months in MONTHS_BY_QUARTER.items():
                total = sum(monthly_totals[m] for m in months if m in monthly_totals)
                if total > 0:
                    q_col = quarter_columns.get(q_status)
                    if not q_col:
                        continue

                    quarterly_totals[q_status] = total
                    obj = existing_items.get(q_col.id)
                    if obj:
                        obj.plan_value = total
                        update_items.append(obj)
                    else:
                        new_items.append(
                            PlantPlanItem(
                                plant_plan=plant_plan,
                                column=q_col,
                                plan_value=total,
                            )
                        )

            # ===== YEARLY =====
            if yearly_column and quarterly_totals:
                yearly_total = sum(quarterly_totals.values())
                obj = existing_items.get(yearly_column.id)
                if obj:
                    obj.plan_value = yearly_total
                    update_items.append(obj)
                else:
                    new_items.append(
                        PlantPlanItem(
                            plant_plan=plant_plan,
                            column=yearly_column,
                            plan_value=yearly_total,
                        )
                    )

        # 🔥 BULK OPS (eng katta yutuq)
        if new_items:
            PlantPlanItem.objects.bulk_create(new_items, batch_size=500)

        if update_items:
            PlantPlanItem.objects.bulk_update(update_items, ["plan_value"], batch_size=500)

    @transaction.atomic
    def create(self, validated_data):
        organization = Organization.objects.get(id=validated_data["organization"])
        statement = Statement.objects.get(id=validated_data["statement"])
        year = validated_data["year"]
        season = validated_data.get("season")

        plan_items = validated_data.get("plan_items", [])
        plants = validated_data.get("plants", [])

        request = self.context.get("request")
        user = getattr(request, "user", None)

        # 🔹 DB-level yoki serializer-level duplicate check
        existing_plan = Plan.objects.filter(
            organization=organization,
            statement=statement,
            year=year,
            season=season,
        ).first()

        if existing_plan:
            raise CustomExceptionError(
                400, {"detail": _("Plan already exists for this organization, statement, year and season")}
            )

        # 🔒 Plan yaratish
        plan = Plan.objects.create(
            organization=organization,
            statement=statement,
            year=year,
            season=season,
        )

        # 🔹 History log
        HistoryActionJournal.objects.create(
            user=user,
            action="add",
            model_name="Plan",
            object_repr=str(plan),
            change_message="Reja yaratildi",
        )

        # 🔹 Plan items yoki PlantPlan saqlash
        if statement.use_plant_plan:
            self._save_plant_plan(plan, statement, plants)
        else:
            self._save_plan_items(plan, statement, plan_items)

        return plan

    @transaction.atomic
    def update(self, instance, validated_data):

        if "organization" in validated_data:
            instance.organization = Organization.objects.get(
                id=validated_data["organization"]
            )

        if "year" in validated_data:
            instance.year = validated_data["year"]

        if "season" in validated_data:
            instance.season = validated_data["season"]

        # ❗ statement odatda o‘zgarmaydi, lekin agar ruxsat bermoqchi bo‘lsang:
        if "statement" in validated_data:
            instance.statement = Statement.objects.get(
                id=validated_data["statement"]
            )

        instance.save()

        if instance.statement.use_plant_plan:
            plants = validated_data.get("plants", [])
            self._save_plant_plan(instance, instance.statement, plants)
        else:
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



# serializers.py
class PlanListSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    statement = serializers.SerializerMethodField()
    plan_items = PlanListItemSerializer(many=True, read_only=True)
    plants = PlantPlanOutSerializer(
        source="plant_plans",
        many=True,
        read_only=True,
    )
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = (
            "id",
            "year",
            "season",
            "created_at",
            "updated_at",
            "organization",
            "statement",
            "plan_items",
            "plants",
        )

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
        if not dt:
            return None
        return timezone.localtime(dt).strftime("%d.%m.%Y %H:%M")


class ColumnPlanItemSerializer(serializers.Serializer):
    column_id = serializers.UUIDField(source="column.id", read_only=True)
    column_name = serializers.SerializerMethodField()
    column_parent_name = serializers.SerializerMethodField()
    plan_value = serializers.DecimalField(
        max_digits=30,
        decimal_places=2,
        read_only=True
    )

    def get_column_name(self, obj):
        lang = self.context.get("lang", "uz")
        return getattr(obj.column, f"title_{lang}", obj.column.title_uz)

    def get_column_parent_name(self, obj):
        lang = self.context.get("lang", "uz")
        column_map = self.context["column_map"]

        parents = []
        parent = obj.column.parent

        while parent:
            parents.append(getattr(parent, f"title_{lang}", parent.title_uz))
            parent = column_map.get(parent.parent_id)

        return " - ".join(reversed(parents)) if parents else None

class PlantPlanGroupSerializer(serializers.Serializer):
    plant_id = serializers.UUIDField()
    plant_name = serializers.CharField()
    items = ColumnPlanItemSerializer(many=True)

