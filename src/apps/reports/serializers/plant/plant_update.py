from django.db import transaction
from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.reports.models import (
    Report, ReportItem, ReportItemInner, StatementColumn
)
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services.individual_general_report import aggregate_individual_report
from apps.reports.services.report_calculate_expressions import calculate_by_expressions


class PlantReportUpdateSerializer(CustomModelSerializer):
    report_items = serializers.ListField(write_only=True)

    class Meta:
        model = Report
        fields = ["id", "deadline", "report_items"]

    def update(self, instance, validated_data):
        """
        Plant-based report update:
        - column + plant_id bo‘yicha ustunlarni yangilash
        - mavjud innerlarni yangilash
        - yangi innerlarni qo‘shish
        - yana ishlatilmayotgan innerlarni o‘chirish
        - hisoblangan ustunlarni tozalash
        - qayta hisoblash
        """

        items_data = validated_data.pop("report_items", [])

        # ==== 1. Column mapping (faqat berilgan columnlar) ====
        column_ids = [item["statement_column"] for item in items_data]
        columns = (
            StatementColumn.objects
            .filter(id__in=column_ids)
            .select_related("statement")
        )
        columns_map = {str(col.id): col for col in columns}

        with transaction.atomic():

            # ==== 2. Report statusni reset qilish (CANCELLED -> SAVED) ====
            if instance.status == Report.StatusChoices.CANCELLED:
                instance.status = Report.StatusChoices.SAVED
                instance.cancel_reason = None
                instance.cancelled_at = None
                instance.save(update_fields=["status", "cancel_reason", "cancelled_at"])

            # ==== 3. Har bir item bo‘yicha qayta ishlash ====
            for item in items_data:
                col_id = str(item["statement_column"])
                column = columns_map.get(col_id)
                if not column:
                    continue

                inners_data = item.get("inners", [])

                # ==== 4. ReportItem olish yoki yaratish ====
                report_item, _ = ReportItem.objects.get_or_create(
                    report=instance,
                    statement_column=column,
                )

                # ==== 5. Mavjud inner mapping ====
                existing = {
                    str(inner.plant_id): inner
                    for inner in report_item.inners.all()
                }

                received_ids = set()
                to_update = []
                to_create = []

                # ==== 6. Yangilash / Yaratish ====
                for inner in inners_data:
                    plant_id = str(inner.get("plant"))
                    value = inner.get("value")
                    received_ids.add(plant_id)

                    if plant_id in existing:
                        obj = existing[plant_id]
                        if str(obj.value) != str(value):      # faqat o‘zgargan bo‘lsa
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

                # Bulk update/create
                if to_update:
                    ReportItemInner.objects.bulk_update(to_update, ["value"])

                if to_create:
                    ReportItemInner.objects.bulk_create(to_create)

                # ==== 7. Ortiqcha innerlarni o‘chirish ====
                to_delete = set(existing.keys()) - received_ids
                if to_delete:
                    ReportItemInner.objects.filter(
                        report_item=report_item,
                        plant_id__in=to_delete
                    ).delete()

            # ==== 8. Eski hisoblangan ustunlarni tozalash ====
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

            # ==== 9. Hisoblash ====
            calculate_fn = ALL_CALCULATORS.get(statement_name)
            if calculate_fn:
                calculate_fn(instance)
            elif instance.statement.calculate_expression:
                calculate_by_expressions(instance)

            # ==== 10. Individual umumlashtirish ====
            aggregate_individual_report(instance)

        return instance


class PlantReportUpdateReadSerializer(CustomModelSerializer):
    report_items = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "deadline", "report_items"]

    def get_report_items(self, obj):
        items = []

        for item in obj.report_items.select_related("statement_column").prefetch_related("inners"):
            # organization columnlarni tashlaymiz
            if item.statement_column.is_organization:
                continue

            items.append({
                "statement_column": str(item.statement_column_id),
                "inners": [
                    {
                        "plant": str(inner.plant_id),
                        "value": inner.value
                    }
                    for inner in item.inners.all()
                ]
            })

        return items




# from django.db import transaction
#
# from rest_framework import serializers
#
# from apps.base.serializers import CustomModelSerializer
# from apps.reports.report_calculate import ALL_CALCULATORS
# from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
# from apps.reports.services.individual_general_report import aggregate_individual_report
# from apps.reports.services.report_calculate_expressions import calculate_by_expressions
#
#
# class PlantReportUpdateSerializer(CustomModelSerializer):
#     report_items = serializers.ListField(write_only=True)
#
#     class Meta:
#         model = Report
#         fields = [
#             "id", "deadline", "report_items"
#         ]
#
#     def update(self, instance, validated_data):
#         """
#         Plant-based reportni update qiladi:
#         - statement_column + plant_id asosida
#         - mavjud inner larni yangilaydi
#         - yo‘q inner larni qo‘shadi
#         - ortiqchalarni o‘chiradi
#         - hisob-kitob funksiyasini ishga tushiradi
#         """
#         items_data = validated_data.pop("report_items", [])
#
#         # ✅ 1. Column mapping
#         column_ids = [item["statement_column"] for item in items_data]
#         columns = StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
#         columns_map = {str(col.id): col for col in columns}
#
#         with transaction.atomic():
#             # ✅ 2. Status qayta tiklash (cancelled -> saved)
#             if instance.status == Report.StatusChoices.CANCELLED:
#                 instance.status = Report.StatusChoices.SAVED
#                 instance.cancel_reason = None
#                 instance.cancelled_at = None
#                 instance.save(update_fields=["status", "cancel_reason", "cancelled_at"])
#
#             # ✅ 3. Har bir report_item ni qayta ishlash
#             for item in items_data:
#                 col_id = str(item["statement_column"])
#                 column = columns_map.get(col_id)
#                 if not column:
#                     continue
#
#                 inners_data = item.get("inners", [])
#
#                 # ✅ 4. ReportItem olish yoki yaratish
#                 report_item, _ = ReportItem.objects.get_or_create(
#                     report=instance,
#                     statement_column=column
#                 )
#
#                 # ✅ 5. Mavjud innerlarni dict qilish (plant_id → obj)
#                 existing_inners = {
#                     str(inner.plant_id): inner
#                     for inner in report_item.inners.all()
#                 }
#
#                 received_plant_ids = set()
#                 to_update = []
#                 to_create = []
#
#                 for inner in inners_data:
#                     plant_id = str(inner.get("plant"))
#                     value = inner.get("value")
#                     received_plant_ids.add(plant_id)
#
#                     if plant_id in existing_inners:
#                         inner_obj = existing_inners[plant_id]
#                         if str(inner_obj.value) != str(value):
#                             inner_obj.value = value
#                             to_update.append(inner_obj)
#                     else:
#                         to_create.append(ReportItemInner(
#                             report_item=report_item,
#                             plant_id=plant_id,
#                             value=value
#                         ))
#
#                 # ✅ 6. Saqlash: update, create
#                 if to_update:
#                     ReportItemInner.objects.bulk_update(to_update, ['value'])
#                 if to_create:
#                     ReportItemInner.objects.bulk_create(to_create)
#
#                 # ✅ 7. Ortiqchalarni o‘chirish
#                 to_delete_ids = set(existing_inners.keys()) - received_plant_ids
#                 if to_delete_ids:
#                     ReportItemInner.objects.filter(
#                         report_item=report_item,
#                         plant_id__in=to_delete_ids
#                     ).delete()
#
#             # ✅ 8. Eski hisoblangan ustunlarni tozalash
#             from apps.reports.calculate_orderings.calculated_columns import CALCULATED_COLUMNS
#             statement_name = instance.statement.name_uz
#             calculated_orderings = CALCULATED_COLUMNS.get(statement_name, [])
#             if calculated_orderings:
#                 StatementColumn_qs = StatementColumn.objects.filter(
#                     statement=instance.statement,
#                     ordering__in=calculated_orderings
#                 )
#                 ReportItem.objects.filter(
#                     report=instance,
#                     statement_column__in=StatementColumn_qs
#                 ).delete()
#
#             # ✅ 9. Hisoblash funksiyasini chaqirish
#             calculate_func = ALL_CALCULATORS.get(statement_name)
#             if calculate_func:
#                 calculate_func(instance)
#             elif instance.statement.calculate_expression:
#                 calculate_by_expressions(instance)
#
#             # ✅ 10. Individual umumlashtirish
#             aggregate_individual_report(instance)
#
#         return instance
