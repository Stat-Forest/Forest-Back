import uuid

from rest_framework import serializers

from django.db import transaction

from apps.general.models import Organization
from apps.base.serializers import CustomSerializer
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.serializers.reports import ReportItemInnerSerializer
from apps.utils.translation import get_lang_code, get_translated_field
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.services.individual_general_report import aggregate_individual_report


class PlantBasedReportItemSerializer(CustomSerializer):
    statement_column = serializers.UUIDField()
    inners = ReportItemInnerSerializer(many=True)


class PlantBasedReportCreateSerializer(CustomSerializer):
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
        current_org_id = None

        with transaction.atomic():
            for item in items_data:
                col_id = str(item["statement_column"])
                column = columns_map.get(col_id)
                if not column:
                    raise serializers.ValidationError(f"Column {col_id} not found")

                inners = item.get("inners", [])
                if column.is_organization:
                    if not inners:
                        raise serializers.ValidationError(f"Missing inners for org column {col_id}")

                    current_org_id = inners[0]["value"]
                    org_instance = Organization.objects.get(id=current_org_id)
                    report_key = (current_org_id, str(column.statement.id))

                    report = Report.objects.filter(
                        organization=org_instance,
                        statement=column.statement,
                        deadline_id=deadline_id,
                        is_individual_general=False
                    ).first()

                    if not report:
                        report = Report.objects.create(
                            organization=org_instance,
                            statement=column.statement,
                            deadline_id=deadline_id,
                            region=org_instance.region,
                            status=Report.StatusChoices.SAVED
                        )

                    reports_map[report_key] = report
                    report_item_id = uuid.uuid4()
                    report_items_buffer.append(ReportItem(
                        id=report_item_id,
                        report=report,
                        statement_column=column
                    ))

                    lang = get_lang_code(self.context)
                    for inner in inners:
                        val = inner["value"]
                        title = getattr(column, f"title_{lang}", "").lower()
                        if title in ["Tashkilot nomi", "Название организации"]:
                            val = get_translated_field(org_instance, "name", lang)
                        report_inners_buffer.append(ReportItemInner(
                            report_item_id=report_item_id,
                            value=val
                        ))
                    continue

                # regular plant-based column
                if not current_org_id:
                    raise serializers.ValidationError("Organization not yet set")

                org_instance = Organization.objects.get(id=current_org_id)
                report_key = (current_org_id, str(column.statement.id))

                if report_key not in reports_map:
                    report = Report.objects.create(
                        organization=org_instance,
                        statement=column.statement,
                        deadline_id=deadline_id,
                        region=org_instance.region,
                        status=Report.StatusChoices.SAVED
                    )
                    reports_map[report_key] = report

                report = reports_map[report_key]
                report_item_id = uuid.uuid4()
                report_items_buffer.append(ReportItem(
                    id=report_item_id,
                    report=report,
                    statement_column=column
                ))

                for inner in inners:
                    report_inners_buffer.append(ReportItemInner(
                        report_item_id=report_item_id,
                        value=inner["value"]
                    ))

            ReportItem.objects.bulk_create(report_items_buffer)
            ReportItemInner.objects.bulk_create(report_inners_buffer)

            for report in reports_map.values():
                statement_name = report.statement.name_uz
                if func := ALL_CALCULATORS.get(statement_name):
                    func(report)
                aggregate_individual_report(report)

        return list(reports_map.values())