from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.base.serializers import CustomModelSerializer
from apps.reports.models import (
    Report, ReportItem, ReportItemInner, StatementColumn
)
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services.individual_general_report import aggregate_individual_report
from apps.reports.services.report_calculate_expressions import calculate_by_expressions


from uuid import UUID


def validate_uuid(value, field):
    try:
        UUID(str(value))
    except Exception:
        raise ValidationError({field: f"{value} — to‘g‘ri UUID emas"})


def is_calculated_column(column: StatementColumn):
    """
    Svodka / formulali / backend hisoblaydigan columnlar
    """
    if getattr(column, "calculate_expression", None):
        return True
    if getattr(column, "is_user_input", True) is False:
        return True
    return False


# ================================
# SERIALIZER
# ================================

class PlantReportUpdateSerializer(CustomModelSerializer):
    report_items = serializers.ListField(write_only=True)

    class Meta:
        model = Report
        fields = ["id", "deadline", "report_items"]

    def update(self, instance, validated_data):

        if instance.source_report:
            raise ValidationError(
                "Svodka (hisoblangan) hisobotni qo‘lda tahrirlab bo‘lmaydi"
            )

        raw_items = validated_data.pop("report_items", [])
        if not raw_items:
            raise ValidationError("report_items bo‘sh yuborildi")

        # ----------------------------------
        # 1️⃣ Collect column ids
        # ----------------------------------

        column_ids = []
        for item in raw_items:
            col_id = item.get("statement_column")
            if not col_id:
                raise ValidationError("statement_column majburiy")

            validate_uuid(col_id, "statement_column")
            column_ids.append(col_id)

        # ----------------------------------
        # 2️⃣ Load columns once
        # ----------------------------------

        columns = StatementColumn.objects.filter(id__in=column_ids)
        columns_map = {str(c.id): c for c in columns}

        if len(columns_map) != len(set(column_ids)):
            raise ValidationError("Baʼzi statement_column topilmadi")

        # ----------------------------------
        # 3️⃣ Load ReportItems + Inners ONCE
        # ----------------------------------

        report_items = (
            ReportItem.objects
            .filter(
                report=instance,
                statement_column_id__in=column_ids
            )
            .select_related("statement_column")
            .prefetch_related("inners")
        )

        item_map = {
            str(i.statement_column_id): i
            for i in report_items
        }

        # ----------------------------------
        # TRANSACTION
        # ----------------------------------

        with transaction.atomic():

            # Status reset
            if instance.status == Report.StatusChoices.CANCELLED:
                instance.status = Report.StatusChoices.SAVED
                instance.cancel_reason = None
                instance.cancelled_at = None
                instance.save(update_fields=["status", "cancel_reason", "cancelled_at"])

            # ----------------------------------
            # 4️⃣ Process columns
            # ----------------------------------

            for item in raw_items:

                column = columns_map[str(item["statement_column"])]
                inners_data = item.get("inners") or []

                # Skip calculated columns
                if is_calculated_column(column):
                    if inners_data:
                        raise ValidationError(
                            f"{column.id} — hisoblangan ustun yuborilmasligi kerak"
                        )
                    continue

                report_item = item_map.get(str(column.id))

                if not report_item:
                    report_item = ReportItem.objects.create(
                        report=instance,
                        statement_column=column
                    )
                    item_map[str(column.id)] = report_item

                # 🔥 RAMdan existing inners (no DB hit)
                existing = {
                    str(inner.plant_id): inner
                    for inner in report_item.inners.all()
                }

                received_ids = set()
                to_update = []
                to_create = []

                for inner in inners_data:
                    plant_id = inner.get("plant")

                    if not plant_id:
                        raise ValidationError(
                            f"{column.id} ustun uchun plant majburiy"
                        )

                    validate_uuid(plant_id, "plant")
                    plant_id = str(plant_id)

                    value = inner.get("value")
                    received_ids.add(plant_id)

                    if plant_id in existing:
                        obj = existing[plant_id]
                        if str(obj.value) != str(value):
                            obj.value = value
                            to_update.append(obj)
                    else:
                        to_create.append(
                            ReportItemInner(
                                report_item=report_item,
                                plant_id=plant_id,
                                value=value
                            )
                        )

                if to_update:
                    ReportItemInner.objects.bulk_update(to_update, ["value"])

                if to_create:
                    ReportItemInner.objects.bulk_create(to_create)

                # Delete removed
                to_delete = set(existing.keys()) - received_ids
                if to_delete:
                    ReportItemInner.objects.filter(
                        report_item=report_item,
                        plant_id__in=to_delete
                    ).delete()

            # ----------------------------------
            # 5️⃣ Clear calculated columns
            # ----------------------------------

            from apps.reports.calculate_orderings.calculated_columns import CALCULATED_COLUMNS

            statement_name = instance.statement.name_uz
            calculated_orderings = CALCULATED_COLUMNS.get(statement_name, [])

            if calculated_orderings:
                calc_cols = StatementColumn.objects.filter(
                    statement=instance.statement,
                    ordering__in=calculated_orderings
                )
                ReportItem.objects.filter(
                    report=instance,
                    statement_column__in=calc_cols
                ).delete()

            # ----------------------------------
            # 6️⃣ Recalculate
            # ----------------------------------

            calculate_fn = ALL_CALCULATORS.get(statement_name)
            if calculate_fn:
                calculate_fn(instance)
            elif instance.statement.calculate_expression:
                calculate_by_expressions(instance)

            aggregate_individual_report(instance)

        return instance


class PlantReportUpdateReadSerializer(CustomModelSerializer):
    report_items = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "deadline", "report_items"]

    def get_report_items(self, obj):
        items = []

        for item in obj.report_items.all():
            if item.statement_column.is_organization:
                continue

            # ✅ inners ham prefetch qilingan
            inners_data = [
                {
                    "plant": str(inner.plant_id) if inner.plant_id else None,
                    "value": inner.value
                }
                for inner in item.inners.all()
            ]

            items.append({
                "statement_column": str(item.statement_column_id),
                "inners": inners_data
            })

        return items
