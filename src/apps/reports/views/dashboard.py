from django.core.cache import cache
from rest_framework.response import Response

from apps.users.models import CustomUser
from apps.base.views import CustomGenericAPIView
from apps.reports.serializers import DashboardStatSerializer
from apps.reports.models import DashboardStat, Report, Deadline


class DashboardStatListView(CustomGenericAPIView):
    serializer_class = DashboardStatSerializer

    def get(self, request, *args, **kwargs):
        cached_data = cache.get('dashboard_stat')
        if cached_data is not None:
            return Response(cached_data)

        CACHE_KEY = 'dashboard_stat'
        DashboardStat.objects.all().delete()
        new_stat = DashboardStat.objects.create(
            sent_reports=Report.objects.filter(status=Report.StatusChoices.SENT).count() or 0,
            returned_reports=Report.objects.filter(status=Report.StatusChoices.CANCELLED).count() or 0,
            accepted_reports=Report.objects.filter(status=Report.StatusChoices.ACCEPTED).count() or 0,
            draft_reports=Report.objects.filter(status=Report.StatusChoices.SAVED).count() or 0,
            responsible_users=CustomUser.objects.count() or 0,
            deadlines=Deadline.objects.count() or 0,
        )
        serializer = DashboardStatSerializer(new_stat)
        cache.set(CACHE_KEY, serializer.data, timeout=5)
        return Response(serializer.data)
