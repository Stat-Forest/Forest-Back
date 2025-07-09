from rest_framework.views import APIView
from rest_framework.response import Response

from django.utils.translation import gettext_lazy as _

from apps.reports.serializers.plant_report import PlantReportInitSerializer
from apps.reports.services.plant_report import get_or_create_report_and_columns


class BasePlantReportAPIView(APIView):
    ilova_title_uz = None

    def get(self, request):
        serializer = PlantReportInitSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        deadline = serializer.validated_data['deadline_id']
        organization = getattr(request.user, 'organization', None)
        if not organization:
            return Response({_("Tashkilot topilmadi.")}, status=400)

        report, report_items = get_or_create_report_and_columns(
            deadline, organization, self.ilova_title_uz
        )

        return Response({
            "report_id": str(report.id),
            "deadline": str(deadline.id),
            "organization": str(organization.id),
            "organization_name": organization.name,
            "statement": str(report.statement.id),
            "statement_name": report.statement.name,
            "period": report.statement.period,
            "status": report.status,
            "created_at": report.created_at.strftime("%d.%m.%Y %H:%M"),
            "report_items": report_items
        })


class KochatReportListAPIView(BasePlantReportAPIView):
    ilova_title_uz = "Ko‘chat-ilovasi"


class NiXolReportListAPIView(BasePlantReportAPIView):
    ilova_title_uz = "Nihol-ilovasi"
