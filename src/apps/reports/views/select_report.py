from rest_framework.response import Response
from rest_framework.views import APIView


from collections import defaultdict
import uuid
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.reports.models import Report
from apps.reports.serializers.reports import ReportAggregateSelectSerializer
from apps.utils.translation import get_lang_code, get_translated_field
from apps.logs.drf_mixins import DRFHistoryMixin


def is_number(val):
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False


def generate_combined_report(report_ids, lang="uz"):
    from apps.reports.models import Report, ReportItem
    reports = Report.objects.filter(id__in=report_ids, status=Report.StatusChoices.ACCEPTED).select_related('statement', 'deadline')

    if reports.count() != len(report_ids):
        raise ValidationError("Faqat ACCEPTED bo‘lgan reportlarni tanlang.")

    first = reports.first()
    statement = first.statement
    deadline = first.deadline

    if any(r.statement_id != statement.id or r.deadline_id != deadline.id for r in reports):
        raise ValidationError("Reportlar bir xil Statement va Deadline ga tegishli bo‘lishi kerak.")

    all_items = ReportItem.objects.filter(report__in=reports).select_related('statement_column').prefetch_related('inners')
    grouped = defaultdict(list)  # {column_id: [value1, value2, ...]}

    for item in all_items:
        for inner in item.inners.all():
            grouped[item.statement_column_id].append(inner.value)

    statement_columns_data = []

    for column in statement.columns.all():
        column_id = column.id
        values = grouped.get(column_id, [])
        inners = []

        if values:
            if is_number(values[0]):
                total = sum(float(v) for v in values if is_number(v))
                inners = [{"id": str(uuid.uuid4()), "value": str(round(total, 2))}]
            else:
                inners = [{"id": str(uuid.uuid4()), "value": v} for v in values]

        statement_columns_data.append({
            "statement_column_id": str(column.id),
            "statement_column_name": get_translated_field(column, "title", lang),
            "inners": inners
        })

    # Final response
    response = {
        "id": "generated",
        "organization": None,
        "organization_name": "Barcha tashkilotlar bo‘yicha umumiy",
        "statement": str(statement.id),
        "statement_name": get_translated_field(statement, "name", lang),
        "deadline": str(deadline.id),
        "period": deadline.submit_at,
        "status": "saved",
        "created_at": timezone.now().strftime("%d.%m.%Y %H:%M"),
        "report_items": [
            {
                "organization_id": "general",
                "organization_name": "Tanlangan tashkilotlar bo‘yicha Jami hisobot",
                "statement_columns": statement_columns_data
            }
        ]
    }

    return response


class ReportAggregateSelectedAPIView(DRFHistoryMixin,APIView):
    def post(self, request):
        serializer = ReportAggregateSelectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report_ids = serializer.validated_data['report_ids']

        lang = get_lang_code(request)

        reports = Report.objects.filter(id__in=report_ids).select_related('organization').prefetch_related(
            'report_items__inners',
            'report_items__statement_column'
        )

        organization_map = {
            str(report.organization_id): get_translated_field(report.organization, "name", lang)
            for report in reports if report.organization
        }

        aggregated_data = {
            "organization_name": "Tanlangan tashkilotlar bo`yicha Jami hisobot",
            "statement_columns": {}
        }

        for report in reports:
            for item in report.report_items.all():
                column = item.statement_column
                col_id = str(column.id)

                if col_id not in aggregated_data["statement_columns"]:
                    aggregated_data["statement_columns"][col_id] = {
                        "statement_column_name": get_translated_field(column, "title", lang),
                        "values": [],
                        "all_numeric": True
                    }

                for inner in item.inners.all():
                    val = inner.value
                    aggregated_data["statement_columns"][col_id]["values"].append(val)

                    if not is_number(val):
                        aggregated_data["statement_columns"][col_id]["all_numeric"] = False

        final_columns = []
        for col_id, col_data in aggregated_data["statement_columns"].items():
            col_name = col_data["statement_column_name"]

            # maxsus ustun: tashkilot nomi bo‘lsa — name ko‘rinishida
            if col_name.strip().lower() in ["название организации", "organization name"]:
                inners = []
                for org_id in col_data["values"]:
                    org_name = organization_map.get(str(org_id), str(org_id))
                    inners.append({
                        "id": str(uuid.uuid4()),
                        "value": org_name
                    })
            elif col_data["all_numeric"]:
                total = sum(float(v) for v in col_data["values"] if is_number(v))
                inners = [{
                    "id": str(uuid.uuid4()),
                    "value": str(round(total, 2))
                }]
            else:
                inners = [{
                    "id": str(uuid.uuid4()),
                    "value": str(v)
                } for v in col_data["values"]]

            final_columns.append({
                "statement_column_name": col_name,
                "inners": inners
            })

        response_data = {
            "organization_id": "general",
            "organization_name": aggregated_data["organization_name"],
            "statement_columns": final_columns
        }

        return Response(response_data, status=200)