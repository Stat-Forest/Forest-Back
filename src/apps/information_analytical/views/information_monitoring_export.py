from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.information_analytical.serializers.forest_monitoring_export import MonitoringExportSerializer
from apps.utils.translation import get_lang_code
from apps.information_analytical.views.forest_monitoring import ForestMonitoringAPIView
from apps.information_analytical.services.monitoring_export import export_monitoring_to_excel


@extend_schema(
    tags=["Information-Analytics"],
    request=MonitoringExportSerializer,
    description="Forest monitoring ma’lumotlarini Excel formatda eksport qilish",
    parameters=[
        OpenApiParameter(
            name="region",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Region kodi (ANDIJON, TOSHKENT, SAMARQAND, ...)"
        ),
        OpenApiParameter(
            name="organization",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Organization UUID"
        ),
        OpenApiParameter(
            name="period",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Davr: Yillik (2025), Choraklik (2025-CHORAKLIK_1), Oylik (2025-01)"
        ),
        OpenApiParameter(
            name="lang",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Til (uz/ru), default: uz",
            enum=["uz", "ru"]
        ),
    ]
)
class ForestMonitoringExportAPIView(APIView):

    def get(self, request):
        # 🔹 Monitoring endpointni chaqiramiz
        monitoring_view = ForestMonitoringAPIView()
        monitoring_view.request = request
        monitoring_response = monitoring_view.get(request)

        if monitoring_response.status_code != 200:
            return monitoring_response

        monitoring_data = monitoring_response.data

        file_path, filename = export_monitoring_to_excel(
            monitoring_data,
            lang=get_lang_code(request)
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
