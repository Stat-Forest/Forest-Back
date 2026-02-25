from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import ListAPIView

from apps.reports.models import Report
from apps.reports.serializers.source_serializers import SourceReportSerializer


KOCHAT_NIHOL_STATEMENT_ID = "64c0e3ea-6d69-4334-b511-2c12e31ef4f2"


@extend_schema(
    tags=["Source-Report"],
    parameters=[
        OpenApiParameter(
            name="organization",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Tashkilot ID bo‘yicha filter (UUID)",
            required=False,
        ),
    ],
)
class AcceptedKochatNiholSourceReportsAPIView(ListAPIView):
    """
    Faqat ACCEPT qilingan 'Ko‘chat va Nihol' reportlar
    Optional filter: ?organization=<uuid>
    """
    serializer_class = SourceReportSerializer

    queryset = (
        Report.objects
        .select_related("organization", "statement", "deadline")
        .filter(
            status=Report.StatusChoices.ACCEPTED,
            statement_id=KOCHAT_NIHOL_STATEMENT_ID
        )
        .order_by("-created_at")
    )

    def get_queryset(self):
        qs = self.queryset

        organization_id = self.request.query_params.get("organization")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)

        return qs