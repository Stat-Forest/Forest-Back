from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.base.views import CustomListAPIView
from apps.billing.scope import is_billing_role
from apps.reports.services.kadastr import is_kadastr_child
from apps.reports.services.filtered_aggregation import build_filtered_payload


@extend_schema(
    tags=["Reports"],
    parameters=[
        OpenApiParameter(
            name="statement",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Statement UUID",
        ),
        OpenApiParameter(
            name="deadline",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
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
        OpenApiParameter(
            name="quarter",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            enum=["q1", "q2", "q3", "q4"],
            description="Quarter filter for Daromad: q1, q2, q3, q4. "
                        "Berilmasa barcha ACCEPTED choraklar umumiy chiqadi.",
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
        quarter = request.query_params.get("quarter")

        if lang not in ("uz", "ru"):
            lang = "uz"

        if quarter and quarter not in ("q1", "q2", "q3", "q4"):
            quarter = None

        if not statement_id or not deadline_id:
            return Response([], status=200)

        # Ijara billing rollari — faqat "O'rmon kadastri va monitoringi" formalari
        if is_billing_role(request.user) and not is_kadastr_child(statement_id):
            raise PermissionDenied("Bu hisobot formasi sizning rolingiz uchun yopiq.")

        try:
            from apps.reports.models import Statement
            statement = Statement.objects.only("id").get(id=statement_id)
        except Exception:
            return Response({"detail": "Invalid statement"}, status=400)

        payload = build_filtered_payload(statement, deadline_id, lang, quarter=quarter)
        return Response(payload, status=200)
