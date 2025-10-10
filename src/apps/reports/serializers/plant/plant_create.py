import uuid
from django.db import transaction
from rest_framework import serializers

from apps.general.models import Organization
from apps.utils.translation import get_lang_code
from apps.base.serializers import CustomSerializer
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.serializers.plant.plant_report_list import PlantReportListSerializer
from apps.reports.services.individual_general_report import aggregate_individual_report


class PlantBasedReportItemSerializer(CustomSerializer):
    statement_column = serializers.UUIDField()
    inners = serializers.ListField(child=serializers.DictField())


class UniversalPlantReportCreateSerializer(CustomSerializer):
    """
    Universal serializer for creating all plant-based reports
    (Ko‘chat-ilovasi, Nihol-ilovasi, Urug‘ harakati, etc.)
    """
    deadline = serializers.UUIDField()
    report_items = PlantBasedReportItemSerializer(many=True)

    def create(self, validated_data):
        items_data = validated_data.pop("report_items")
        deadline_id = validated_data.get("deadline")

        column_ids = [item["statement_column"] for item in items_data]
        columns = StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
        columns_map = {str(col.id): col for col in columns}

        report_items_buffer = []
        report_inners_buffer = []
        reports_map = {}
        current_org = None

        with transaction.atomic():
            for item in items_data:
                col_id = str(item["statement_column"])
                column = columns_map.get(col_id)
                if not column:
                    raise serializers.ValidationError(f"Column {col_id} not found")

                inners = item.get("inners", [])

                # ✅ 1. "Tashkilot nomi" column -> org_id dan tashkilotni aniqlash
                if column.is_organization:
                    if not inners or not inners[0].get("value"):
                        raise serializers.ValidationError("Tashkilot ID kiritilishi kerak.")
                    org_id = inners[0]["value"]
                    try:
                        current_org = Organization.objects.get(id=org_id)
                    except Organization.DoesNotExist:
                        raise serializers.ValidationError(f"Tashkilot topilmadi: {org_id}")
                    continue

                # ✅ 2. Org aniqlanmagan bo‘lsa xato
                if not current_org:
                    raise serializers.ValidationError(
                        "Tashkilot aniqlanmagan, iltimos 'Tashkilot nomi' columnni yuboring."
                    )

                # ✅ 3. Reportni yaratamiz yoki olamiz
                report_key = (current_org.id, column.statement.id)
                if report_key not in reports_map:
                    report = Report.objects.create(
                        organization=current_org,
                        statement=column.statement,
                        deadline_id=deadline_id,
                        region=current_org.region,
                        status=Report.StatusChoices.SAVED,
                        is_plant_based=True,
                    )
                    reports_map[report_key] = report

                report = reports_map[report_key]
                report_item_id = uuid.uuid4()

                # ✅ ReportItem
                report_items_buffer.append(
                    ReportItem(
                        id=report_item_id,
                        report=report,
                        statement_column=column
                    )
                )

                # ✅ Innerlar
                for inner in inners:
                    report_inners_buffer.append(
                        ReportItemInner(
                            report_item_id=report_item_id,
                            plant_id=inner.get("plant"),
                            value=inner.get("value")
                        )
                    )

            ReportItem.objects.bulk_create(report_items_buffer)
            ReportItemInner.objects.bulk_create(report_inners_buffer)

            # ✅ Hisob-kitob
            for report in reports_map.values():
                if func := ALL_CALCULATORS.get(report.statement.name_uz):
                    func(report)
                aggregate_individual_report(report)

        # ✅ Natija uchun instance
        self.instance = list(reports_map.values())
        return self.instance

    # ✅ create dan keyingi response formatini sozlaymiz
    def to_representation(self, instance_list):
        lang = get_lang_code(self.context)
        serialized = []

        for report in instance_list:
            serialized.append(PlantReportListSerializer(
                report,
                context={"request": self.context.get("request")}
            ).data)

        return serialized
