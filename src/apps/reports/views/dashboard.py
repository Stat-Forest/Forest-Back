from rest_framework.response import Response
from apps.users.models import CustomUser
from apps.reports.models import Report, Deadline, Plan
from apps.base.views import CustomGenericAPIView
from apps.reports.serializers import DashboardStatSerializer
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Dashboards"])
class DashboardStatListView(CustomGenericAPIView):
    serializer_class = DashboardStatSerializer

    def get(self, request, *args, **kwargs):
        user = request.user

        if not user.organization and not user.statement:
            report_qs = Report.objects.all()
            deadline_qs = Deadline.objects.all()
            responsible_users = CustomUser.objects.count()
            plans = Plan.objects.all().count()

        elif user.statement:
            report_qs = Report.objects.filter(statement__parent_id=user.statement.id)
            deadline_qs = Deadline.objects.filter(
                statement__parent_id=user.statement.id
            )
            responsible_users = CustomUser.objects.filter(
                statement_id=user.statement.id
            ).count()
            plans = Plan.objects.filter(statement__parent_id=user.statement.id).count()

        elif user.organization:
            report_qs = Report.objects.filter(organization_id=user.organization.id)
            deadline_qs = Deadline.objects.filter(
                organizations__in=[user.organization]
            )
            responsible_users = CustomUser.objects.filter(
                organization_id=user.organization.id
            ).count()
            plans = Plan.objects.filter(organization_id=user.organization.id).count()

        else:
            return Response({"detail": "Invalid user context."}, status=400)

        data = {
            "sent_reports": report_qs.filter(status=Report.StatusChoices.SENT).count(),
            "returned_reports": report_qs.filter(status=Report.StatusChoices.CANCELLED).count(),
            "accepted_reports": report_qs.filter(status=Report.StatusChoices.ACCEPTED).count(),
            "draft_reports": report_qs.filter(status=Report.StatusChoices.SAVED).count(),
            "responsible_users": responsible_users,
            "deadlines": deadline_qs.count(),
            "plans": plans,
        }

        serializer = DashboardStatSerializer(data)
        return Response(serializer.data)
