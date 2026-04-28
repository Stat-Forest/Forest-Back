from uuid import UUID

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.base.serializers import CustomModelSerializer
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services.individual_general_report import aggregate_individual_report
from apps.reports.services.quarter_validator import DaromadQuarterService
from apps.reports.services.report_calculate_expressions import calculate_by_expressions


def validate_uuid(value, field):
    try:
        UUID(str(value))
    except Exception:
        raise ValidationError({field: f"{value} — неверный UUID"})


def is_calculated_column(column: StatementColumn) -> bool:
    if getattr(column, "calculate_expression", None):
        return True
    if getattr(column, "is_user_input", True) is False:
        return True
    return False


class PlantReportUpdateSerializer(CustomModelSerializer):
    report_items = serializers.ListField(write_only=True)
    quarter = serializers.ChoiceField(
        choices=Report.QuarterChoices.choices,
        required=False,
        allow_null=True,
        help_text="Daromad uchun qaysi chorak update qilinayotgani",
    )

    class Meta:
        model = Report
        fields = ["id", "deadline", "quarter", "report_items"]

    def validate(self, attrs):
        instance = self.instance
        quarter = attrs.get("quarter")
        raw_items = attrs.get("report_items") or []

        if not raw_items:
            raise ValidationError({"report_items": "report_items bo'sh bo'lishi mumkin emas."})

        column_ids = []
        for item in raw_items:
            col_id = item.get("statement_column")
            if not col_id:
                raise ValidationError({"statement_column": "statement_column majburiy."})
            column_ids.append(col_id)

        if DaromadQuarterService.is_daromad_report(instance):
            DaromadQuarterService.validate_update(
                report=instance,
                requested_quarter=quarter,
            )
            DaromadQuarterService.validate_columns_for_quarter(
                statement=instance.statement,
                quarter=quarter,
                column_ids=column_ids,
                allow_common=True,
            )
        else:
            if quarter:
                raise ValidationError({
                    "quarter": "Bu hisobot uchun chorak tanlash shart emas."
                })

        return attrs

    def update(self, instance, validated_data):
        if instance.source_report:
            raise ValidationError(
                "Svodный (hisoblangan) reportni qo'lda tahrirlab bo'lmaydi."
            )

        raw_items = validated_data.pop("report_items", [])
        quarter = validated_data.get("quarter")

        payload_by_column_id: dict[str, list] = {}
        ordered_column_ids: list[str] = []

        for item in raw_items:
            col_id = item.get("statement_column")
            if not col_id:
                raise ValidationError({"statement_column": "statement_column majburiy."})
            validate_uuid(col_id, "statement_column")

            col_id = str(col_id)
            ordered_column_ids.append(col_id)
            payload_by_column_id[col_id] = item.get("inners") or []

        unique_column_ids = list(dict.fromkeys(ordered_column_ids))

        columns = list(
            StatementColumn.objects
            .filter(id__in=unique_column_ids, statement=instance.statement)
            .only(
                "id",
                "ordering",
                "title",
                "title_uz",
                "is_user_input",
                "is_organization",
                "status_plan",
            )
        )
        columns_map = {str(c.id): c for c in columns}

        if len(columns_map) != len(unique_column_ids):
            raise ValidationError(
                "Ba'zi statement_column lar topilmadi yoki bu statement ga tegishli emas."
            )

        existing_report_items = list(
            ReportItem.objects
            .filter(report=instance, statement_column_id__in=unique_column_ids)
            .only("id", "statement_column_id")
        )
        item_map = {str(item.statement_column_id): item for item in existing_report_items}

        created_report_items = []
        for column_id in unique_column_ids:
            column = columns_map[column_id]
            inners_data = payload_by_column_id.get(column_id, [])

            if is_calculated_column(column):
                if inners_data:
                    raise ValidationError(
                        f"{column.id} — hisoblanadigan column, unga data yuborib bo'lmaydi."
                    )
                continue

            if column_id not in item_map:
                created_report_items.append(
                    ReportItem(
                        report=instance,
                        statement_column=column,
                    )
                )

        with transaction.atomic():
            if DaromadQuarterService.is_daromad_report(instance):
                DaromadQuarterService.prepare_report_for_update(
                    report=instance,
                    quarter=quarter,
                )
                instance.save(update_fields=[
                    "quarter",
                    "current_quarter",
                    "status",
                    DaromadQuarterService.get_quarter_status_field(quarter),
                    "quarter_status_dates",
                ])
            elif instance.status == Report.StatusChoices.CANCELLED:
                instance.status = Report.StatusChoices.SAVED
                instance.cancel_reason = None
                instance.cancelled_at = None
                instance.save(update_fields=["status", "cancel_reason", "cancelled_at"])

            if created_report_items:
                ReportItem.objects.bulk_create(created_report_items)

            report_items = list(
                ReportItem.objects
                .filter(report=instance, statement_column_id__in=unique_column_ids)
                .only("id", "statement_column_id")
            )
            item_map = {str(item.statement_column_id): item for item in report_items}

            report_item_ids = [item.id for item in report_items]
            existing_inners = list(
                ReportItemInner.objects
                .filter(report_item_id__in=report_item_ids)
                .only("id", "report_item_id", "plant_id", "value")
            )

            inners_by_item_id: dict[str, dict[str, ReportItemInner]] = {}
            for inner in existing_inners:
                if inner.plant_id is None:
                    continue
                inners_by_item_id.setdefault(str(inner.report_item_id), {})[str(inner.plant_id)] = inner

            inner_updates = []
            inner_creates = []
            inner_delete_ids = []

            for column_id in unique_column_ids:
                column = columns_map[column_id]
                if is_calculated_column(column):
                    continue

                report_item = item_map[column_id]
                current_inners = inners_by_item_id.get(str(report_item.id), {})
                inners_data = payload_by_column_id.get(column_id, [])

                received_ids = set()

                for inner in inners_data:
                    plant_id = inner.get("plant")
                    if not plant_id:
                        raise ValidationError(
                            f"{column.id} column uchun plant majburiy."
                        )

                    validate_uuid(plant_id, "plant")
                    plant_id = str(plant_id)
                    value = inner.get("value")
                    received_ids.add(plant_id)

                    existing = current_inners.get(plant_id)
                    if existing:
                        if str(existing.value) != str(value):
                            existing.value = value
                            inner_updates.append(existing)
                    else:
                        inner_creates.append(
                            ReportItemInner(
                                report_item=report_item,
                                plant_id=plant_id,
                                value=value,
                            )
                        )

                to_delete = set(current_inners.keys()) - received_ids
                if to_delete:
                    inner_delete_ids.extend(
                        inner.id
                        for pid, inner in current_inners.items()
                        if pid in to_delete
                    )

            if inner_updates:
                ReportItemInner.objects.bulk_update(inner_updates, ["value"])

            if inner_creates:
                ReportItemInner.objects.bulk_create(inner_creates)

            if inner_delete_ids:
                ReportItemInner.objects.filter(id__in=inner_delete_ids).delete()

            from apps.reports.calculate_orderings.calculated_columns import CALCULATED_COLUMNS

            statement_name = getattr(instance.statement, "name_uz", None) or instance.statement.name
            calculated_orderings = CALCULATED_COLUMNS.get(statement_name, [])

            if calculated_orderings:
                calc_col_ids = list(
                    StatementColumn.objects.filter(
                        statement=instance.statement,
                        ordering__in=calculated_orderings,
                    ).values_list("id", flat=True)
                )
                if calc_col_ids:
                    ReportItem.objects.filter(
                        report=instance,
                        statement_column_id__in=calc_col_ids,
                    ).delete()

            calculate_fn = ALL_CALCULATORS.get(statement_name)
            if calculate_fn:
                calculate_fn(instance)
            elif instance.statement.calculate_expression:
                calculate_by_expressions(instance)

            aggregate_individual_report(instance)

        return instance


class PlantReportUpdateReadSerializer(CustomModelSerializer):
    quarter_info = serializers.SerializerMethodField()
    report_items = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "deadline", "quarter", "current_quarter", "quarter_info", "report_items"]

    def get_quarter_info(self, obj):
        if not DaromadQuarterService.is_daromad_report(obj):
            return None

        access = DaromadQuarterService.get_quarter_access_info(obj)

        return {
            "quarter_1_status": obj.quarter_1_status,
            "quarter_2_status": obj.quarter_2_status,
            "quarter_3_status": obj.quarter_3_status,
            "quarter_4_status": obj.quarter_4_status,
            "quarter_1_dates": DaromadQuarterService.get_quarter_dates(obj, "q1"),
            "quarter_2_dates": DaromadQuarterService.get_quarter_dates(obj, "q2"),
            "quarter_3_dates": DaromadQuarterService.get_quarter_dates(obj, "q3"),
            "quarter_4_dates": DaromadQuarterService.get_quarter_dates(obj, "q4"),
            "current_quarter": access.current_quarter,
            "next_quarter": access.next_available_quarter,
            "can_create": access.can_create,
            "can_update": access.can_update,
            "can_edit_current_quarter": obj.can_edit_current_quarter,
        }

    def get_report_items(self, obj):
        if DaromadQuarterService.is_daromad_report(obj):
            access = DaromadQuarterService.get_quarter_access_info(obj)
            target_quarter = access.next_available_quarter or obj.current_quarter

            if not target_quarter:
                return []

            allowed_orderings = set(
                DaromadQuarterService.get_manual_input_orderings(target_quarter)
            )

            items = []
            for item in obj.report_items.all():
                column = item.statement_column

                if column.is_organization:
                    continue

                if column.status_plan or column.ordering in allowed_orderings:
                    items.append({
                        "statement_column": str(item.statement_column_id),
                        "inners": [
                            {
                                "plant": str(inner.plant_id) if inner.plant_id else None,
                                "value": inner.value,
                            }
                            for inner in item.inners.all()
                        ],
                    })
            return items

        return [
            {
                "statement_column": str(item.statement_column_id),
                "inners": [
                    {
                        "plant": str(inner.plant_id) if inner.plant_id else None,
                        "value": inner.value,
                    }
                    for inner in item.inners.all()
                ],
            }
            for item in obj.report_items.all()
            if not item.statement_column.is_organization
        ]