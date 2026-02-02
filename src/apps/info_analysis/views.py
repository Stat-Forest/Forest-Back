from debug_toolbar.utils import is_processable_html_response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.reports.models import Report
from apps.reports.models import Report as ReportModel
from apps.info_analysis.static_filter import REPORT_DASHBOARD_COLUMNS
from apps.info_analysis.dashboard_value import get_report_item_value
from apps.info_analysis.deadline_filters import apply_deadline_filter
from apps.info_analysis.calc import calculate_diff_and_percent


class ReportAnalysisDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Reports | Dashboard"],
        summary="Report Info dashboard",
        description="Faqat ACCEPTED bo‘lgan reportlar asosida dashboard ma’lumotlari",
        parameters=[
            OpenApiParameter(
                name="region",
                type=OpenApiTypes.STR,
                required=False,
                description="Viloyat kodi yoki REPUBLIC"
            ),
            OpenApiParameter(
                name="organization",
                type=OpenApiTypes.UUID,
                required=False,
                description="Organization UUID"
            ),

            # ===== DEADLINE FILTERS =====
            OpenApiParameter(
                name="daily",
                type=OpenApiTypes.STR,
                required=False,
                description="Kunlik: YYYY-MM-DD"
            ),
            OpenApiParameter(
                name="weekly",
                type=OpenApiTypes.STR,
                required=False,
                description="Haftalik: YYYY-MM-HAFTALIK_1"
            ),
            OpenApiParameter(
                name="monthly",
                type=OpenApiTypes.STR,
                required=False,
                description="Oylik: YYYY-MM"
            ),
            OpenApiParameter(
                name="quarterly",
                type=OpenApiTypes.STR,
                required=False,
                description="Choraklik: YYYY-CHORAK_1"
            ),
            OpenApiParameter(
                name="yearly",
                type=OpenApiTypes.STR,
                required=False,
                description="Yillik: YYYY"
            ),
        ],
    )
    def post(self, request):
        data = request.data

        # =============================
        # BASE QUERY (FAQAT ACCEPTED)
        # =============================
        reports = Report.objects.filter(
            status=ReportModel.StatusChoices.ACCEPTED
        )

        # =============================
        # REGION FILTER
        # =============================
        region = data.get("region")
        if region == "REPUBLIC":
            reports = reports.filter(is_republic=True,is_report=False)
        else:
            reports = reports.filter(region=region,is_report=False)

        # =============================
        # ORGANIZATION FILTER
        # =============================
        organization = data.get("organization")
        if organization:
            reports = reports.filter(organization_id=organization)

        computed_values = {}
        response_items = []

        for col in sorted(REPORT_DASHBOARD_COLUMNS, key=lambda x: x["data_ordering"]):

            # =============================
            # PLAN / ACTUAL
            # =============================
            if col["type"] in ("plan", "actual"):
                filtered_reports = apply_deadline_filter(
                    queryset=reports,
                    period=col["period"],
                    params=data
                )

                value = get_report_item_value(filtered_reports, col)
                computed_values[col["key"]] = value

                response_items.append({
                    "column_title": col["column_title"],
                    "value": value
                })

            # =============================
            # DIFF / PERCENT
            # =============================
            else:
                plan_key, actual_key = col["depends_on"]
                plan = computed_values.get(plan_key, 0)
                actual = computed_values.get(actual_key, 0)

                diff, percent = calculate_diff_and_percent(plan, actual)
                value = diff if col["type"] == "diff" else percent

                response_items.append({
                    "column_title": "Farqi" if col["type"] == "diff" else "Foiz (%)",
                    "value": value
                })

        return Response({
            "region": region,
            "organization": organization,
            "result": response_items
        })
