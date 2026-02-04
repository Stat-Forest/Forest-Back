from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.base.views import CustomGenericAPIView
from apps.reports.serializers.dashboard import DashboardStatSerializer
from apps.reports.views.dashboard.dashboard_stat_service import DashboardStatService


@extend_schema(tags=["Dashboards"])
class DashboardStatListView(CustomGenericAPIView):
    serializer_class = DashboardStatSerializer

    def get(self, request, *args, **kwargs):
        service = DashboardStatService(request.user)
        data = service.get_stats()
        return Response(data)
