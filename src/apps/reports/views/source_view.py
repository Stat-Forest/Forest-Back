from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import ListAPIView

from apps.reports.models import Report
from apps.reports.serializers.source_serializers import SourceReportSerializer


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
            statement__name_uz="Ko‘chat va Nihol"
        )
        .order_by("-created_at")
    )

    def get_queryset(self):
        qs = self.queryset

        organization_id = self.request.query_params.get("organization")
        if organization_id:
            qs = qs.filter(organization_id=organization_id)

        return qs