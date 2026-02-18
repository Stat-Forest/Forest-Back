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


def validate_uuid(value, field_name="id"):
    try:
        UUID(str(value))
    except Exception:
        raise ValidationError({field_name: f"{value} to‘g‘ri UUID emas"})


class PlantReportUpdateSerializer(CustomModelSerializer):
    report_items = serializers.ListField(write_only=True)

    class Meta:
        model = Report
        fields = ["id", "deadline", "report_items"]

    def update(self, instance, validated_data):

        raw_items = validated_data.pop("report_items", [])

        # =====================================================
        # 🛡 DEFENSIVE CLEANING (frontend xatolaridan himoya)
        # =====================================================
        items_data = []

        for item in raw_items:
            col = item.get("statement_column")

            if col is None:
                raise ValidationError({"statement_column": "Majburiy maydon"})

            validate_uuid(col, "statement_column")

            items_data.append(item)

        if not items_data:
            raise ValidationError("report_items bo‘sh yoki noto‘g‘ri yuborildi.")

        # =====================================================
        # 1️⃣ Column mapping
        # =====================================================
        column_ids = []
        for item in items_data:
            try:
                column_ids.append(item["statement_column"])
            except KeyError:
                raise ValidationError("statement_column majburiy maydon")

        columns = (
            StatementColumn.objects
            .filter(id__in=column_ids)
            .select_related("statement")
        )

        columns_map = {str(col.id): col for col in columns}

        if not columns_map:
            raise ValidationError("Berilgan statement_column lar topilmadi.")

        # =====================================================
        # 2️⃣ TRANSACTION
        # =====================================================
        with transaction.atomic():

            # ---- Status reset ----
            if instance.status == Report.StatusChoices.CANCELLED:
                instance.status = Report.StatusChoices.SAVED
                instance.cancel_reason = None
                instance.cancelled_at = None
                instance.save(update_fields=["status", "cancel_reason", "cancelled_at"])

            # =================================================
            # 3️⃣ Item loop
            # =================================================
            for item in items_data:
                col_id = str(item["statement_column"])
                column = columns_map.get(col_id)

                if not column:
                    continue

                inners_data = item.get("inners") or []

                report_item, _ = ReportItem.objects.get_or_create(
                    report=instance,
                    statement_column=column,
                )

                existing = {
                    str(inner.plant_id): inner
                    for inner in report_item.inners.all()
                }

                received_ids = set()
                to_update = []
                to_create = []

                # =============================
                # 4️⃣ Inner loop
                # =============================
                for inner in inners_data:
                    plant_id = inner.get("plant")

                    if not plant_id:
                        continue   # None plant ham serverni yiqitmasin

                    value = inner.get("value")
                    plant_id = str(plant_id)

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

                # =============================
                # 5️⃣ Delete removed inners
                # =============================
                to_delete = set(existing.keys()) - received_ids
                if to_delete:
                    ReportItemInner.objects.filter(
                        report_item=report_item,
                        plant_id__in=to_delete
                    ).delete()

            # =================================================
            # 6️⃣ Clear calculated columns
            # =================================================
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

            # =================================================
            # 7️⃣ Recalculate
            # =================================================
            calculate_fn = ALL_CALCULATORS.get(statement_name)
            if calculate_fn:
                calculate_fn(instance)
            elif instance.statement.calculate_expression:
                calculate_by_expressions(instance)

            # =================================================
            # 8️⃣ Individual jami
            # =================================================
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
