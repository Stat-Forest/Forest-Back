from django.core.cache import cache
from rest_framework.response import Response

from apps.users.models import CustomUser
from apps.reports.models import Report,Deadline
from apps.base.views import CustomGenericAPIView
from apps.reports.serializers import DashboardStatSerializer

from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Dashboards"])
class DashboardStatListView(CustomGenericAPIView):
    serializer_class = DashboardStatSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        organization= user.organization
        is_global_user = not organization
        cache_key = f'dashboard_stat_{"all" if is_global_user else "_".join(str(organization.id))}'

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        report_qs = Report.objects.all() if is_global_user else Report.objects.filter(organization_id=organization.id)
        deadline_qs = Deadline.objects.all() if is_global_user else Deadline.objects.filter(
            organizations__in=organization).distinct()

        data = {
            "sent_reports": report_qs.filter(status=Report.StatusChoices.SENT).count(),
            "returned_reports": report_qs.filter(status=Report.StatusChoices.CANCELLED).count(),
            "accepted_reports": report_qs.filter(status=Report.StatusChoices.ACCEPTED).count(),
            "draft_reports": report_qs.filter(status=Report.StatusChoices.SAVED).count(),
            "responsible_users": CustomUser.objects.filter(
                organization_id=organization.id).count() if not is_global_user else CustomUser.objects.count(),
            "deadlines": deadline_qs.count(),
        }

        serializer = DashboardStatSerializer(data)
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data)
