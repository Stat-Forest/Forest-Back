from django.core.cache import cache
from drf_spectacular.utils import extend_schema

from rest_framework.response import Response

from apps.users.models import CustomUser
from apps.base.views import CustomGenericAPIView
from apps.reports.serializers import DashboardStatSerializer
from apps.reports.models import Report, Deadline, DashboardStat


@extend_schema(tags=["Dashboards"])
class DashboardStatListView(CustomGenericAPIView):
    serializer_class = DashboardStatSerializer
    queryset = DashboardStat.objects.none()

    def get(self, request, *args, **kwargs):
        CACHE_KEY = 'dashboard_stat'
        cached_data = cache.get(CACHE_KEY)
        if cached_data is not None:
            return Response(cached_data)

        data = {
            "sent_reports": Report.objects.filter(status=Report.StatusChoices.SENT).count(),
            "returned_reports": Report.objects.filter(status=Report.StatusChoices.CANCELLED).count(),
            "accepted_reports": Report.objects.filter(status=Report.StatusChoices.ACCEPTED).count(),
            "draft_reports": Report.objects.filter(status=Report.StatusChoices.SAVED).count(),
            "responsible_users": CustomUser.objects.count(),
            "deadlines": Deadline.objects.count(),
        }

        serializer = DashboardStatSerializer(data)
        cache.set(CACHE_KEY, serializer.data, timeout=300)
        return Response(serializer.data)
