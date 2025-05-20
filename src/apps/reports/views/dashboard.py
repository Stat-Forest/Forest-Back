from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from apps.users.models import CustomUser
from apps.base.views import CustomGenericAPIView
from apps.reports.serializers import DashboardStatSerializer
from apps.reports.models import Report, Deadline


@extend_schema(tags=["Dashboards"])
class DashboardStatListView(CustomGenericAPIView):
    serializer_class = DashboardStatSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        organizations = user.organizations.all()
        is_global_user = not organizations.exists()
        cache_key = f'dashboard_stat_{"all" if is_global_user else "_".join(str(org.id) for org in organizations)}'

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        report_qs = Report.objects.all() if is_global_user else Report.objects.filter(organization__in=organizations)
        deadline_qs = Deadline.objects.all() if is_global_user else Deadline.objects.filter(
            organizations__in=organizations).distinct()

        data = {
            "sent_reports": report_qs.filter(status=Report.StatusChoices.SENT).count(),
            "returned_reports": report_qs.filter(status=Report.StatusChoices.CANCELLED).count(),
            "accepted_reports": report_qs.filter(status=Report.StatusChoices.ACCEPTED).count(),
            "draft_reports": report_qs.filter(status=Report.StatusChoices.SAVED).count(),
            "responsible_users": CustomUser.objects.filter(
                organizations__in=organizations).distinct().count() if not is_global_user else CustomUser.objects.count(),
            "deadlines": deadline_qs.count(),
        }

        serializer = DashboardStatSerializer(data)
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data)
