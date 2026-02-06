from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.response import Response

from apps.base.views import CustomListAPIView
from apps.reports.services.filtered_aggregation import parse_period, build_filtered_payload


@extend_schema(
    tags=["Reports"],
    parameters=[
        OpenApiParameter(
            name="statement",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Statement UUID",
        ),
        OpenApiParameter(
            name="deadline",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Period filter: YYYY or YYYY-Qn (e.g., 2025 or 2025-Q2)",
        ),
        OpenApiParameter(
            name="lang",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            enum=["uz", "ru"],
            description="Language for column titles",
        ),
    ],
)
class FilteredGeneralReportAPIView(CustomListAPIView):
    """
    Read-only, in-memory filtered aggregates by period (quarter/year).
    Does NOT write to DB and does NOT trigger existing aggregation signals.
    """
    pagination_class = None

    def list(self, request, *args, **kwargs):
        statement_id = request.query_params.get("statement")
        deadline_id = request.query_params.get("deadline")
        lang = (request.query_params.get("lang") or "uz").lower()

        if lang not in ("uz", "ru"):
            lang = "uz"

        if not statement_id or not deadline_id:
            return Response({"detail": "statement and period are required"}, status=400)

        try:
            from apps.reports.models import Statement
            statement = Statement.objects.only("id").get(id=statement_id)
        except Exception:
            return Response({"detail": "Invalid statement"}, status=400)

        payload = build_filtered_payload(statement, deadline_id, lang)
        return Response(payload, status=200)
