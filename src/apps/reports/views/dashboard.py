from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.users.models import CustomUser
from apps.reports.models import Report, Deadline, Plan
from apps.base.views import CustomGenericAPIView
from apps.reports.serializers import DashboardStatSerializer


@extend_schema(tags=["Dashboards"])
class DashboardStatListView(CustomGenericAPIView):
    serializer_class = DashboardStatSerializer
    permission_classes = [IsAuthenticated]  

    def get(self, request, *args, **kwargs):
        user = request.user

        organization = getattr(user, "organization", None)
        statement = getattr(user, "statement", None)

        is_global_user = not organization and not statement
        is_admin_user = not statement and organization

        if is_global_user:
            cache_key = 'dashboard_stat_all'
        elif is_admin_user:
            cache_key = f'dashboard_stat_admin_{organization.id}'
        elif organization:
            cache_key = f'dashboard_stat_{organization.id}'
        else:
            return Response({"detail": "Invalid user context."}, status=400)

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        if is_global_user:
            report_qs = Report.objects.all()
            deadline_qs = Deadline.objects.all()
            responsible_users = CustomUser.objects.all()
            plans = Plan.objects.all()

        elif is_admin_user:
            report_qs = Report.objects.filter(statement_id=statement.pk)
            deadline_qs = Deadline.objects.filter(statement__parent_id=statement.pk)
            responsible_users = CustomUser.objects.filter(statement_id=statement.pk)
            plans = Plan.objects.filter(statement__parent_id=statement.pk)

        else:
            report_qs = Report.objects.filter(organization_id=organization.pk)
            deadline_qs = Deadline.objects.filter(organizations=organization).distinct()
            responsible_users = CustomUser.objects.filter(organization_id=organization.pk)
            plans = Plan.objects.filter(organization_id=organization.pk)

        data = {
            "sent_reports": report_qs.filter(status=Report.StatusChoices.SENT).count(),
            "returned_reports": report_qs.filter(status=Report.StatusChoices.CANCELLED).count(),
            "accepted_reports": report_qs.filter(status=Report.StatusChoices.ACCEPTED).count(),
            "draft_reports": report_qs.filter(status=Report.StatusChoices.SAVED).count(),
            "responsible_users": responsible_users.count(),
            "deadlines": deadline_qs.count(),
            "plans": plans.count(),
        }

        serializer = DashboardStatSerializer(data)
        cache.set(cache_key, serializer.data, timeout=1)

        return Response(serializer.data)
