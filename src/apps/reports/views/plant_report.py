from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.reports.serializers.plant_report import PlantReportInitSerializer
from apps.reports.services.plant_report import get_or_create_report_and_columns


class PlantReportListAPIView(APIView):
    def get(self, request):
        serializer = PlantReportInitSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        deadline = serializer.validated_data['deadline_id']
        organization = getattr(request.user, 'organization', None)
        if not organization:
            return Response({"detail": "Foydalanuvchida tashkilot (organization) mavjud emas."},
                            status=status.HTTP_400_BAD_REQUEST)

        report, result = get_or_create_report_and_columns(deadline, organization)

        return Response({
            "report_id": report.id,
            "deadline": str(deadline.id),
            "organization": str(organization.id),
            "organization_name": organization.name,
            "statement": str(report.statement.id),
            "statement_name": report.statement.name,
            "period": report.statement.period,
            "status": report.status,
            "created_at": report.created_at.strftime("%d.%m.%Y %H:%M"),
            "report_items": result
        }, status=status.HTTP_200_OK)
