from datetime import date
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema

from apps.users.models import CustomUser
from apps.reports.models import Report, Deadline, Plan
from apps.base.views import CustomGenericAPIView
from apps.reports.serializers.dashboard import DashboardStatSerializer


@extend_schema(tags=["Dashboards"])
class DashboardStatListView(CustomGenericAPIView):
    serializer_class = DashboardStatSerializer

    def get(self, request, *args, **kwargs):
        user = request.user

        if not user.organization and not user.statement:
            report_qs = Report.objects.filter(is_report=True)
            deadline_qs = Deadline.objects.all()
            responsible_users = CustomUser.objects.count()
            plans = Plan.objects.all().count()

        elif user.statement:
            report_qs = Report.objects.filter(
                statement__parent_id=user.statement.id,
                is_report=True
            )
            deadline_qs = Deadline.objects.filter(
                statement__parent_id=user.statement.id
            )
            responsible_users = CustomUser.objects.filter(
                statement_id=user.statement.id
            ).count()
            plans = Plan.objects.filter(
                statement__parent_id=user.statement.id
            ).count()

        elif user.organization:
            report_qs = Report.objects.filter(
                organization_id=user.organization.id,
                is_report=True
            )
            deadline_qs = Deadline.objects.filter(
                organizations__in=[user.organization]
            )
            responsible_users = CustomUser.objects.filter(
                organization_id=user.organization.id
            ).count()
            plans = Plan.objects.filter(
                organization_id=user.organization.id
            ).count()

        else:
            return Response(
                {"detail": _("Invalid user context.")},
                status=400
            )

        # ===== expired_deadlines LOGIC (FIXED) =====
        expired_deadlines_count = 0

        expired_deadlines_qs = (
            deadline_qs
            .filter(deadline_at__lt=date.today())
            .prefetch_related("organizations")
        )

        for deadline in expired_deadlines_qs:

            if user.role in {
                CustomUser.Role.TASHKILOT_RAHBARI,
                CustomUser.Role.TASHKILOT_HODIMI
            }:
                if not user.organization:
                    continue

                report_exists = Report.objects.filter(
                    deadline=deadline,
                    organization_id=user.organization.id,
                    is_report=True,
                ).exists()

                if not report_exists:
                    expired_deadlines_count += 1

            else:
                for org in deadline.organizations.all():
                    report_exists = Report.objects.filter(
                        deadline=deadline,
                        organization=org,
                        is_report=True,
                    ).exists()

                    if not report_exists:
                        expired_deadlines_count += 1
                        break  # bitta organization yetarli

        data = {
            "sent_reports": report_qs.filter(
                status=Report.StatusChoices.SENT
            ).count(),
            "returned_reports": report_qs.filter(
                status=Report.StatusChoices.CANCELLED
            ).count(),
            "accepted_reports": report_qs.filter(
                status=Report.StatusChoices.ACCEPTED
            ).count(),
            "draft_reports": report_qs.filter(
                status=Report.StatusChoices.SAVED
            ).count(),
            "responsible_users": responsible_users,
            "deadlines": deadline_qs.count(),
            "plans": plans,
            "on_time_reports": report_qs.filter(
                status=Report.StatusChoices.ACCEPTED,
                time_status=Report.TimeStatus.ON_TIME
            ).count(),
            "late_reports": report_qs.filter(
                status=Report.StatusChoices.ACCEPTED,
                time_status=Report.TimeStatus.LATE
            ).count(),
            "expired_deadlines": expired_deadlines_count,
        }

        serializer = DashboardStatSerializer(data)
        return Response(serializer.data)
