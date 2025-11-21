import uuid

from rest_framework import serializers
from django.db import transaction

from apps.base.serializers import CustomModelSerializer
from apps.reports.calculate_orderings.calculated_columns import CALCULATED_COLUMNS
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services import aggregate_individual_report
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

        if instance.status == Report.StatusChoices.CANCELLED:
            instance.status = Report.StatusChoices.SAVED
            instance.cancel_reason = None
            instance.cancelled_at = None
            instance.save(update_fields=["status", "cancel_reason", "cancelled_at"])

        deadline = validated_data.get("deadline", instance.deadline)
        column_ids = [item["statement_column"] for item in items_data]

        columns = StatementColumn.objects.filter(
            id__in=column_ids,
            is_user_input=True
        ).select_related("statement")

        columns_map = {str(c.id): c for c in columns}

        # columns_map = {
        #     str(c.id): c
        #     for c in StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
        # }

        organization_name = instance.organization.name

        with transaction.atomic():
            for item in items_data:
                col_id = item["statement_column"]
                column = columns_map.get(col_id)

                if not column:
                    continue

                inners_data = item.get("inners", [])

                # 1. ReportItem-ni olish yoki yaratish
                report_item, _ = ReportItem.objects.get_or_create(
                    report=instance,
                    statement_column=column
                )

                # 2. Mavjud inners-ni olish (dict: id → obj)
                existing_inners = {
                    str(inner.id): inner
                    for inner in report_item.inners.all()
                }

                existing_inner_ids = set(existing_inners.keys())
                received_inner_ids = set()

                for inner_data in inners_data:
                    inner_id = str(inner_data.get("id", ""))
                    value = inner_data["value"]

                    if column.title_uz.strip().lower() == "tashkilot nomi":
                        value = organization_name

                    # 2a. Update bor bo‘lsa
                    if inner_id and inner_id in existing_inners:
                        inner_obj = existing_inners[inner_id]
                        inner_obj.value = value
                        inner_obj.save()
                        received_inner_ids.add(inner_id)
                    else:
                        # 2b. Yangi obyekt yaratish
                        ReportItemInner.objects.create(
                            report_item=report_item,
                            value=value
                        )

                # 3. Ortiqcha (frontenddan kelmagan) `inners` ni o‘chirish
                to_delete_ids = existing_inner_ids - received_inner_ids
                if to_delete_ids:
                    ReportItemInner.objects.filter(id__in=to_delete_ids).delete()

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

            # 6. Individual, viloyat, respublika jami
            aggregate_individual_report(instance)

        return instance


class ReportDetailSerializer(CustomModelSerializer):
    report_items = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "deadline", "report_items"]

    def get_report_items(self, obj):
        items = obj.report_items.filter(statement_column__is_user_input=True)
        return ReportItemUpdateSerializer(items, many=True).data