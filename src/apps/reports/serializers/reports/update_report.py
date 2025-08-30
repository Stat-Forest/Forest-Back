import uuid

from rest_framework import serializers
from django.db import transaction

from apps.base.serializers import CustomModelSerializer
from apps.reports.calculate_orderings.calculated_columns import CALCULATED_COLUMNS
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services import aggregate_individual_report, aggregate_general_report, aggregate_national_report
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


class ReportItemInnerSerializer(CustomModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = ReportItemInner
        fields = ["id", "value"]

    def get_value(self, obj):
        try:
            if obj.report_item.statement_column.is_organization:
                return str(obj.value)
        except Exception:
            pass
        return obj.value


class ReportItemUpdateSerializer(serializers.ModelSerializer):
    inners = serializers.SerializerMethodField()

    class Meta:
        model = ReportItem
        fields = ["statement_column", "inners"]

    def get_inners(self, obj):
        return ReportItemInnerSerializer(obj.inners.all(), many=True).data


class ReportUpdateSerializer(serializers.ModelSerializer):
    report_items = serializers.ListField(write_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "deadline",
            "report_items"
        ]

    def update(self, instance, validated_data):
        items_data = validated_data.pop("report_items")
        deadline = validated_data.get("deadline", instance.deadline)

        column_ids = [item["statement_column"] for item in items_data]
        columns_map = {
            str(c.id): c
            for c in StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
        }

        organization_id = instance.organization_id
        organization_name = instance.organization.name

        report_items_buffer = []
        report_inners_buffer = []

        with transaction.atomic():
            for item in items_data:
                col_id = item["statement_column"]
                column = columns_map.get(col_id)

                if not column:
                    raise serializers.ValidationError({"detail": f"Invalid column {col_id}"})

                inners_data = item.get("inners", [])

                # 1. Eski ustunni va ichki qiymatlarini tozalash
                ReportItemInner.objects.filter(
                    report_item__report=instance,
                    report_item__statement_column=column
                ).delete()

                ReportItem.objects.filter(
                    report=instance,
                    statement_column=column
                ).delete()

                # 2. Yangi qiymatlarni bufferga yig‘ish
                report_item_id = uuid.uuid4()
                report_items_buffer.append(
                    ReportItem(
                        id=report_item_id,
                        report=instance,
                        statement_column=column
                    )
                )
                for inner in inners_data:
                    value = inner["value"]

                    # 🔥 Tashkilot nomi ustuni uchun value ni tashkilot nomi qilib yozamiz
                    if column.title_uz.strip().lower() == "tashkilot nomi":
                        value = organization_name

                    report_inners_buffer.append(
                        ReportItemInner(
                            report_item_id=report_item_id,
                            value=value
                        )
                    )

            # 3. Yangi qiymatlarni bulk_create bilan saqlash
            ReportItem.objects.bulk_create(report_items_buffer, batch_size=1000)
            ReportItemInner.objects.bulk_create(report_inners_buffer, batch_size=2000)

            # 4. Eski hisoblangan ustunlarni o‘chirish (CALCULATED_COLUMNS asosida)
            statement_name = instance.statement.name_uz
            calculated_orderings = CALCULATED_COLUMNS.get(statement_name, [])
            if calculated_orderings:
                StatementColumn_qs = StatementColumn.objects.filter(
                    statement=instance.statement,
                    ordering__in=calculated_orderings
                )
                ReportItem.objects.filter(
                    report=instance,
                    statement_column__in=StatementColumn_qs
                ).delete()

            # 5. Hisoblash funksiyasini chaqirish
            calculate_func = ALL_CALCULATORS.get(statement_name)
            if calculate_func:
                calculate_func(instance)

            # 6. Individual Jami hisoblash
            aggregate_individual_report(instance)

            aggregate_general_report(instance.statement, instance.deadline, instance.region)

            aggregate_national_report(instance.statement, instance.deadline, instance.region)

        return instance


class ReportDetailSerializer(CustomModelSerializer):
    report_items = ReportItemUpdateSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = ["id", "deadline", "report_items"]