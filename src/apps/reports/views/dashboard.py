from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.users.models import CustomUser
from apps.reports.models import Report, Deadline, Plan


@extend_schema(tags=["Dashboards"])
class DashboardStatListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        organization = getattr(user, 'organization', None)
        statement = getattr(user, 'statement', None)

        if organization:
            report_qs = Report.objects.filter(organization_id=organization.pk)
            responsible_users = CustomUser.objects.filter(organization_id=organization.pk)
            deadline_qs = Deadline.objects.filter(organizations=organization).distinct()
            plans = Plan.objects.filter(organization_id=organization.pk)

        elif statement:
            report_qs = Report.objects.filter(statement_id=statement.pk)
            deadline_qs = Deadline.objects.filter(statement__parent_id=statement.pk)
            responsible_users = CustomUser.objects.filter(statement_id=statement.pk)
            plans = Plan.objects.filter(statement__parent_id=statement.pk)

        else:
            report_qs = Report.objects.all()
            deadline_qs = Deadline.objects.all()
            responsible_users = CustomUser.objects.all()
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

        return Response(data, status=200)
