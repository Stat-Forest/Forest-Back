from datetime import date
# pyrefly: ignore [missing-import]
from django.core.cache import cache
# pyrefly: ignore [missing-import]
from django.db.models import Count, Exists, OuterRef, Q

# pyrefly: ignore [missing-import]
from apps.reports.models import Report, Deadline, Plan, Statement
# pyrefly: ignore [missing-import]
from apps.users.models import CustomUser

# Report saqlanganda dashboard_signal keshni tozalaydi, shuning uchun uzoq TTL xavfsiz.
DASHBOARD_CACHE_TTL = 300


class DashboardStatService:

    def __init__(self, user):
        self.user = user

    @property
    def cache_key(self):
        from apps.reports.signals.dashboard_signal import get_dashboard_version
        return f"dashboard:stats:v{get_dashboard_version()}:user:{self.user.id}"

    # ================= PUBLIC API =================
    def get_stats(self):
        cached_data = cache.get(self.cache_key)
        if cached_data:
            return cached_data

        data = self._calculate_stats()
        cache.set(self.cache_key, data, DASHBOARD_CACHE_TTL)
        return data

    # ================= BASE CONTEXT =================gklNX2189oisAIOXD@
    def _get_base_context(self):
        user = self.user

        # SUPER / MARKAZIY
        if user.role in {
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.RAHBARIYAT,
        } and not user.organization and not user.statement:
            return {
                "reports": Report.objects.filter(is_report=True),
                "deadlines": Deadline.objects.all(),
                "users": CustomUser.objects.all(),
                "plans": Plan.objects.all(),
            }

        # SUPPORT ADMIN
        if user.role == CustomUser.Role.SUPPORT_ADMIN:
            return {
                "reports": Report.objects.none(),
                "deadlines": Deadline.objects.none(),
                "users": CustomUser.objects.filter(
                    role=CustomUser.Role.SUPPORT_ADMIN
                ),
                "plans": Plan.objects.none(),
            }

        # STATEMENT
        if user.statement:
            return {
                "reports": Report.objects.filter(
                    statement__parent_id=user.statement_id,
                    is_report=True
                ),
                "deadlines": Deadline.objects.filter(
                    statement__parent_id=user.statement_id
                ),
                "users": CustomUser.objects.filter(
                    statement_id=user.statement_id
                ),
                "plans": Plan.objects.filter(
                    statement__parent_id=user.statement_id
                ),
            }

        # HUDUDIY BOSHQARMA
        if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            orgs = list(user.region_user_orgs.all())
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
    def _count_deadlines_with_missing_report(self, expired_qs, org_ids=None):
        """
        Kamida bitta (doiradagi) tashkiloti ACCEPTED hisobot topshirmagan
        muddatlar soni. 3 ta so'rov — muddatlar va tashkilotlar soniga bog'liq
        emas (ilgari har bir muddat × tashkilot uchun exists() edi).
        """
        deadline_ids = list(expired_qs.values_list("id", flat=True).distinct())
        if not deadline_ids:
            return 0

        pairs = Deadline.organizations.through.objects.filter(deadline_id__in=deadline_ids)
        if org_ids is not None:
            pairs = pairs.filter(organization_id__in=org_ids)
        pairs = pairs.values_list("deadline_id", "organization_id")

        accepted = set(
            Report.objects.filter(
                deadline_id__in=deadline_ids,
                is_report=True,
                status=Report.StatusChoices.ACCEPTED,
            ).values_list("deadline_id", "organization_id")
        )
        return len({d for d, o in pairs if (d, o) not in accepted})

    def _get_expired_deadlines_count(self, deadlines_qs):
        user = self.user
        expired_qs = deadlines_qs.filter(deadline_at__lt=date.today())

        # SUPER_ADMIN — barcha orglar bo'yicha tekshiradi
        if user.role in {
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.RAHBARIYAT,
        }:
            return self._count_deadlines_with_missing_report(expired_qs)

        # SUPPORT ADMIN
        if user.role == CustomUser.Role.SUPPORT_ADMIN:
            return 0

        # ORGANIZATION USER — faqat o'z orgi bo'yicha
        if user.role in {
            CustomUser.Role.TASHKILOT_RAHBARI,
            CustomUser.Role.TASHKILOT_HODIMI
        }:
            base_report_qs = Report.objects.filter(
                deadline=OuterRef("pk"),
                organization=user.organization,
                is_report=True,
                status=Report.StatusChoices.ACCEPTED,
            )
            return expired_qs.annotate(
                has_report=Exists(base_report_qs)
            ).filter(has_report=False).count()

        # HUDUDIY BOSHQARMA — o'z mintaqasidagi orglar bo'yicha
        if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            org_ids = list(user.region_user_orgs.values_list("id", flat=True))
            if not org_ids:
                return 0
            return self._count_deadlines_with_missing_report(expired_qs, org_ids)

        # OTHER ROLES
        base_report_qs = Report.objects.filter(
            deadline=OuterRef("pk"),
            is_report=True,
            status=Report.StatusChoices.ACCEPTED,
        )
        return expired_qs.annotate(
            has_report=Exists(base_report_qs)
        ).filter(has_report=False).count()

    # ================= MAIN CALCULATION =================
    def _calculate_stats(self):
        ctx = self._get_base_context()

        reports = ctx["reports"]
        deadlines = ctx["deadlines"]
        users = ctx["users"]
        plans = ctx["plans"]

        S = Report.StatusChoices
        T = Report.TimeStatus
        # Hisobotlar bo'yicha barcha sonlar — bitta so'rov (ilgari 10 ta COUNT)
        r = reports.order_by().aggregate(
            total=Count("id"),
            sent=Count("id", filter=Q(status=S.SENT)),
            returned=Count("id", filter=Q(status=S.CANCELLED)),
            accepted=Count("id", filter=Q(status=S.ACCEPTED)),
            draft=Count("id", filter=Q(status=S.SAVED)),
            on_time=Count("id", filter=Q(status=S.ACCEPTED, time_status=T.ON_TIME)),
            late=Count("id", filter=Q(status=S.ACCEPTED, time_status=T.LATE)),
        )
        st = Statement.objects.order_by().aggregate(
            father=Count("id", filter=Q(parent__isnull=True)),
            child=Count("id", filter=Q(parent__isnull=False)),
        )

        return {
            "total_reports": r["total"] or 0,
            "sent_reports": r["sent"] or 0,
            "returned_reports": r["returned"] or 0,
            "accepted_reports": r["accepted"] or 0,
            "draft_reports": r["draft"] or 0,
            "responsible_users": users.count(),
            "deadlines": deadlines.count(),
            "plans": plans.count(),
            "on_time_reports": r["on_time"] or 0,
            "late_reports": r["late"] or 0,
            "expired_deadlines": self._get_expired_deadlines_count(deadlines),
            "father_statements": st["father"] or 0,
            "child_statements": st["child"] or 0,
        }
