from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reports.services.dashboard_overview import DashboardOverviewService


@extend_schema(
    tags=["Dashboards"],
    parameters=[
        OpenApiParameter("lang", OpenApiTypes.STR, enum=["uz", "ru"], required=False),
        OpenApiParameter("period", OpenApiTypes.STR, enum=["month", "quarter", "year", "all"], required=False),
    ],
    responses=OpenApiTypes.OBJECT,
)
class DashboardOverviewAPIView(APIView):
    """Bosh sahifa: hisobotlar statistikasi (foydalanuvchi doirasida, 5 daqiqa kesh)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        service = DashboardOverviewService(
            request.user,
            lang=request.query_params.get("lang"),
            period=request.query_params.get("period"),
        )
        return Response(service.get())
