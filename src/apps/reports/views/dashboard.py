from django.core.cache import cache
from rest_framework.response import Response

from apps.users.models import CustomUser
from apps.reports.models import Report, Deadline,Plan
from apps.base.views import CustomGenericAPIView
from apps.reports.serializers import DashboardStatSerializer

from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Dashboards"])
class DashboardStatListView(CustomGenericAPIView):
    serializer_class = DashboardStatSerializer

    def get(self, request, *args, **kwargs):
        user = request.user

        if user.organization is not None:
            report_qs= Report.objects.filter(organization_id=user.organization.pk)
            responsible_users = CustomUser.objects.filter(organization_id=user.organization.pk)
            deadline_qs = Deadline.objects.filter(organizations=user.organization).distinct()
            plans = Plan.objects.filter(organization_id=user.organization.pk)

        elif user.statement is not None:
            report_qs = Report.objects.filter(statement_id=user.statement.pk)
            deadline_qs = Deadline.objects.filter(statement__parent_id=user.statement.pk)
            responsible_users = CustomUser.objects.filter(statement_id=user.statement.pk)
            plans = Plan.objects.filter(statement__parent_id=user.statement.pk)
        else:
            report_qs = Report.objects.all()
            deadline_qs = Deadline.objects.all()
            responsible_users = CustomUser.all()
            plans = Plan.objects.all()

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
        return Response(serializer.data,status=200)
