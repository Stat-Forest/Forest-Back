# apps/reports/views/dashboard/dashboard_stat_service.py
from datetime import date
from django.core.cache import cache
from django.db.models import Exists, OuterRef

from apps.reports.models import Report, Deadline, Plan
from apps.users.models import CustomUser


DASHBOARD_CACHE_TTL = 10  # seconds


class DashboardStatService:

    def __init__(self, user):
        self.user = user
        self.cache_key = f"dashboard:stats:user:{user.id}"

    # ================= PUBLIC API =================
    def get_stats(self):
        cached_data = cache.get(self.cache_key)
        if cached_data:
            return cached_data

        data = self._calculate_stats()
        cache.set(self.cache_key, data, DASHBOARD_CACHE_TTL)
        return data

    # ================= BASE CONTEXT =================
    def _get_base_context(self):
        user = self.user

        # SUPER / MARKAZIY
        if not user.organization and not user.statement:
            return {
                "reports": Report.objects.filter(is_report=True),
                "deadlines": Deadline.objects.all(),
                "users": CustomUser.objects.all(),
                "plans": Plan.objects.all(),
            }

        # STATEMENT
        if user.statement:
            return {
                "reports": Report.objects.filter(
                    statement__parent_id=user.statement.id,
                    is_report=True
                ),
                "deadlines": Deadline.objects.filter(
                    statement__parent_id=user.statement.id
                ),
                "users": CustomUser.objects.filter(
                    statement_id=user.statement.id
                ),
                "plans": Plan.objects.filter(
                    statement__parent_id=user.statement.id
                ),
            }

        # HUDUDIY BOSHQARMA
        if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            orgs = user.region_user_orgs.all()
            return {
                "reports": Report.objects.filter(
                    organization__in=orgs,
                    is_report=True
                ),
                "deadlines": Deadline.objects.filter(
                    organizations__in=orgs
                ).distinct(),
                "users": CustomUser.objects.filter(
                    organization__in=orgs
                ),
                "plans": Plan.objects.filter(
                    organization__in=orgs
                ),
            }

        # ORGANIZATION
        if user.organization:
            return {
                "reports": Report.objects.filter(
                    organization=user.organization,
                    is_report=True
                ),
                "deadlines": Deadline.objects.filter(
                    organizations=user.organization
                ),
                "users": CustomUser.objects.filter(
                    organization=user.organization
                ),
                "plans": Plan.objects.filter(
                    organization=user.organization
                ),
            }

        raise ValueError("Invalid user context")

    # ================= EXPIRED DEADLINES =================
    def _get_expired_deadlines_count(self, deadlines_qs):
        user = self.user

        base_report_qs = Report.objects.filter(
            deadline=OuterRef("pk"),
            is_report=True
        )

        # ORGANIZATION USER
        if user.role in {
            CustomUser.Role.TASHKILOT_RAHBARI,
            CustomUser.Role.TASHKILOT_HODIMI
        }:
            expired = deadlines_qs.filter(
                deadline_at__lt=date.today()
            ).annotate(
                has_report=Exists(
                    base_report_qs.filter(organization=user.organization)
                )
            ).filter(has_report=False)

            return expired.count()

        # HUDUDIY BOSHQARMA
        if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            orgs = user.region_user_orgs.all()

            expired = deadlines_qs.filter(
                deadline_at__lt=date.today(),
                organizations__in=orgs
            ).distinct().annotate(
                has_report=Exists(
                    base_report_qs.filter(organization__in=orgs)
                )
            ).filter(has_report=False)

            return expired.count()

        # OTHERS
        expired = deadlines_qs.filter(
            deadline_at__lt=date.today()
        ).annotate(
            has_report=Exists(base_report_qs)
        ).filter(has_report=False)

        return expired.count()

    # ================= MAIN CALCULATION =================
    def _calculate_stats(self):
        ctx = self._get_base_context()

        reports = ctx["reports"]
        deadlines = ctx["deadlines"]
        users = ctx["users"]
        plans = ctx["plans"]

        return {
            "sent_reports": reports.filter(
                status=Report.StatusChoices.SENT
            ).count(),
            "returned_reports": reports.filter(
                status=Report.StatusChoices.CANCELLED
            ).count(),
            "accepted_reports": reports.filter(
                status=Report.StatusChoices.ACCEPTED
            ).count(),
            "draft_reports": reports.filter(
                status=Report.StatusChoices.SAVED
            ).count(),
            "responsible_users": users.count(),
            "deadlines": deadlines.count(),
            "plans": plans.count(),
            "on_time_reports": reports.filter(
                status=Report.StatusChoices.ACCEPTED,
                time_status=Report.TimeStatus.ON_TIME
            ).count(),
            "late_reports": reports.filter(
                status=Report.StatusChoices.ACCEPTED,
                time_status=Report.TimeStatus.LATE
            ).count(),
            "expired_deadlines": self._get_expired_deadlines_count(deadlines),
        }
