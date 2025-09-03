# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext_lazy as _

from apps.reports.serializers.reports import PlantReportInitSerializer
from apps.reports.serializers.plant.plant_create import PlantBasedReportCreateSerializer
from apps.reports.services.plant_report import get_or_create_report_and_columns


class PlantBasedReportInitAPIView(APIView):
    statement_name = None  # default

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view.cls.statement_name = initkwargs.get("statement_name")
        return view

    def post(self, request):
        serializer = PlantReportInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        deadline = serializer.validated_data['deadline_id']
        organization = getattr(request.user, 'organization', None)

        if not organization:
            return Response({"detail": _("Tashkilot topilmadi.")}, status=status.HTTP_400_BAD_REQUEST)

        # ⬇️ statement_name ni endi classdan olamiz
        report, report_items = get_or_create_report_and_columns(
            deadline, organization, self.statement_name
        )

        response_data = {
            "id": str(report.id),
            "deadline": str(deadline.id),
            "organization": str(organization.id),
            "organization_name": organization.name,
            "statement": str(report.statement.id),
            "statement_name": report.statement.name,
            "period": report.statement.period,
            "status": report.status,
            "created_at": report.created_at.strftime("%d.%m.%Y %H:%M"),
            "report_items": report_items
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class PlantBasedReportCreateAPIView(APIView):
    """
    POST: Submit values to plant-based reports (Ko‘chat, Nihol).
    """
    def post(self, request):
        serializer = PlantBasedReportCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": _("Hisobotlar saqlandi.")}, status=status.HTTP_201_CREATED)
