"""
Bosh sahifa (login'dan keyin) uchun hisobotlar statistikasi — bitta agregat javob.

    GET /api/v1/reports/dashboard/overview/?lang=uz|ru&period=month|quarter|year|all

Hamma hisob-kitob foydalanuvchi doirasida: hisobotlar `scope_reports_for_user`,
muddat↔tashkilot topshiriqlari `scope_deadline_assignments_for_user` orqali
(tashkilot xodimi — o'z tashkiloti, bo'lim admini — o'z bo'limi, hududiy — o'z
hududlari, billing rollari — faqat kadastr bo'limi, markaziy rollar — hammasi).

So'rovlar agregat (Count + filter, TruncMonth), N+1 yo'q; natija 5 daqiqa
foydalanuvchi doirasi kaliti bo'yicha keshlanadi.
"""
import hashlib
from datetime import date, datetime, time, timedelta

from django.db.models import Count, Exists, OuterRef, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.reports.models import Deadline, Report, Statement
from apps.reports.permissions.report_scope import (
    FULL_ACCESS_ROLES,
    scope_deadline_assignments_for_user,
    scope_reports_for_user,
)
from apps.reports.services.report_cache import get_report_list_version
from apps.users.models import CustomUser
from apps.utils.cache_list import cache_get_or_set
from apps.utils.services import RegionChoices
from apps.utils.translation import get_lang_code, get_translated_field

OVERVIEW_CACHE_TTL = 300  # 5 daqiqa
PERIOD_DAYS = {"month": 30, "quarter": 90, "year": 365, "all": None}
DEFAULT_PERIOD = "year"
STATUSES = ("accepted", "sent", "saved", "cancelled")
TREND_MONTHS = 12
UPCOMING_DAYS = 14
TOP_FORMS_LIMIT = 8
UPCOMING_LIMIT = 8

Assignment = Deadline.organizations.through


def normalize_period(value) -> str:
    return value if value in PERIOD_DAYS else DEFAULT_PERIOD


def _pct(part, whole):
    return round(part * 100.0 / whole, 1) if whole else 0.0


def _change_pct(current, previous):
    if previous is None or not previous:
        return None
    return round((current - previous) * 100.0 / previous, 1)


def _start_of_day(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time.min))


def _shift_month(day: date, months: int) -> date:
    index = day.year * 12 + (day.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


class DashboardOverviewService:

    def __init__(self, user, *, lang="uz", period=DEFAULT_PERIOD, today: date | None = None):
        self.user = user
        self.lang = get_lang_code(lang)
        self.period = normalize_period(period)
        self.today = today or timezone.localdate()

    # ================= SCOPE =================
    def _scope(self):
        """(level, cache signature) — keshi bir xil doiradagi foydalanuvchilar uchun umumiy."""
        user = self.user
        if user.is_superuser or user.role in FULL_ACCESS_ROLES:
            return "all", "all"
        if user.role in (CustomUser.Role.BILLING_USER, CustomUser.Role.BILLING_SUPER):
            return "kadastr", f"billing:{user.pk}"
        if user.role in (CustomUser.Role.TASHKILOT_HODIMI, CustomUser.Role.TASHKILOT_RAHBARI):
            return "organization", f"org:{user.organization_id}"
        if user.role == CustomUser.Role.BOLIM_ADMIN:
            return "department", f"dept:{user.statement_id}"
        if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            regions = sorted(set(user.region_user_orgs.values_list("region", flat=True)))
            return "region", "region:" + ",".join(regions)
        return "none", f"none:{user.role}"

    def _reports(self):
        return scope_reports_for_user(Report.objects.filter(is_report=True), self.user)

    def _assignments(self):
        return scope_deadline_assignments_for_user(
            Assignment.objects.filter(deadline__deadline_at__isnull=False), self.user
        )

    # ================= PUBLIC =================
    def cache_key(self) -> str:
        _, signature = self._scope()
        raw = f"{signature}|{self.lang}|{self.period}|{self.today.isoformat()}"
        return "dashboard:overview:" + hashlib.sha1(raw.encode()).hexdigest()

    def get(self) -> dict:
        return cache_get_or_set(
            key=self.cache_key(),
            version=get_report_list_version(),
            ttl=OVERVIEW_CACHE_TTL,
            compute=self.build,
        )

    def build(self) -> dict:
        level, _ = self._scope()
        days = PERIOD_DAYS[self.period]
        start = self.today - timedelta(days=days - 1) if days else None
        prev_start = start - timedelta(days=days) if days else None

        reports = self._reports()
        kpis = self._kpis(reports, start, prev_start)
        regions = self._regions(reports, start)
        return {
            "period": self.period,
            "period_start": start.isoformat() if start else None,
            "period_end": self.today.isoformat(),
            "generated_at": timezone.now().isoformat(),
            "scope": {"level": level, "regions_count": len(regions)},
            "kpis": kpis,
            "acceptance_rate": _pct(kpis["accepted"]["value"], kpis["total"]["value"]),
            "monthly": self._monthly(reports),
            "discipline": self._discipline(start),
            "top_forms": self._top_forms(reports, start),
            "regions": regions if len(regions) > 1 else [],
            "upcoming_deadlines": self._upcoming(),
        }

    # ================= KPI =================
    def _kpis(self, reports, start, prev_start):
        aggregates = {}
        current = Q(created_at__gte=_start_of_day(start)) if start else Q()
        aggregates["total"] = Count("id", filter=current)
        for status in STATUSES:
            aggregates[status] = Count("id", filter=current & Q(status=status))
        if start:
            previous = Q(created_at__gte=_start_of_day(prev_start), created_at__lt=_start_of_day(start))
            aggregates["prev_total"] = Count("id", filter=previous)
            for status in STATUSES:
                aggregates[f"prev_{status}"] = Count("id", filter=previous & Q(status=status))
        row = reports.aggregate(**aggregates)

        total = row["total"]
        result = {}
        for key in ("total",) + STATUSES:
            value = row[key]
            previous = row.get(f"prev_{key}") if start else None
            result[key] = {
                "value": value,
                "previous": previous,
                "change_pct": _change_pct(value, previous),
                "share_pct": _pct(value, total) if key != "total" else 100.0 if total else 0.0,
            }
        return result

    # ================= MONTHLY TREND =================
    def _monthly(self, reports):
        first_month = _shift_month(self.today.replace(day=1), -(TREND_MONTHS - 1))
        rows = (
            reports.filter(created_at__gte=_start_of_day(first_month))
            .annotate(month=TruncMonth("created_at"))
            .values("month", "status")
            .annotate(count=Count("id"))
        )
        buckets = {}
        for i in range(TREND_MONTHS):
            month = _shift_month(first_month, i)
            buckets[(month.year, month.month)] = {"month": f"{month.year:04d}-{month.month:02d}", "total": 0,
                                                  **{s: 0 for s in STATUSES}}
        for row in rows:
            month = row["month"]
            bucket = buckets.get((month.year, month.month)) if month else None
            if bucket is None or row["status"] not in STATUSES:
                continue
            bucket[row["status"]] += row["count"]
            bucket["total"] += row["count"]
        return list(buckets.values())

    # ================= DEADLINE DISCIPLINE =================
    def _report_exists(self, **filters):
        qs = Report.objects.filter(
            is_report=True,
            deadline_id=OuterRef("deadline_id"),
            organization_id=OuterRef("organization_id"),
            **filters,
        )
        return Exists(scope_reports_for_user(qs, self.user))

    def _annotated_assignments(self, qs):
        accepted = Report.StatusChoices.ACCEPTED
        return qs.annotate(
            acc_late=self._report_exists(status=accepted, time_status=Report.TimeStatus.LATE),
            acc_any=self._report_exists(status=accepted),
            sent_any=self._report_exists(status=Report.StatusChoices.SENT),
        )

    def _discipline(self, start):
        qs = self._assignments().filter(deadline__deadline_at__lt=self.today)
        if start:
            qs = qs.filter(deadline__deadline_at__gte=start)
        row = self._annotated_assignments(qs).aggregate(
            total=Count("id"),
            on_time=Count("id", filter=Q(acc_any=True, acc_late=False)),
            late=Count("id", filter=Q(acc_late=True)),
            in_review=Count("id", filter=Q(acc_any=False, sent_any=True)),
            missing=Count("id", filter=Q(acc_any=False, sent_any=False)),
        )
        total = row["total"]
        return {
            **row,
            "on_time_rate": _pct(row["on_time"], total),
            "completion_rate": _pct(row["on_time"] + row["late"], total),
        }

    # ================= TOP FORMS =================
    def _top_forms(self, reports, start):
        qs = reports.filter(created_at__gte=_start_of_day(start)) if start else reports
        rows = list(
            qs.values("statement_id")
            .annotate(
                total=Count("id"),
                accepted=Count("id", filter=Q(status=Report.StatusChoices.ACCEPTED)),
                cancelled=Count("id", filter=Q(status=Report.StatusChoices.CANCELLED)),
            )
            .order_by("-total", "statement_id")[:TOP_FORMS_LIMIT]
        )
        statements = Statement.objects.select_related("parent").in_bulk([r["statement_id"] for r in rows])
        result = []
        for row in rows:
            statement = statements.get(row["statement_id"])
            result.append({
                "id": str(row["statement_id"]),
                "name": get_translated_field(statement, "name", self.lang),
                "parent_name": get_translated_field(statement.parent, "name", self.lang) if statement else "",
                "total": row["total"],
                "accepted": row["accepted"],
                "cancelled": row["cancelled"],
                "acceptance_rate": _pct(row["accepted"], row["total"]),
            })
        return result

    # ================= REGIONS =================
    def _regions(self, reports, start):
        qs = reports.filter(created_at__gte=_start_of_day(start)) if start else reports
        rows = (
            qs.filter(organization__isnull=False)
            .values("organization__region")
            .annotate(
                total=Count("id"),
                **{s: Count("id", filter=Q(status=s)) for s in STATUSES},
            )
            .order_by("-total")
        )
        labels = dict(RegionChoices.choices)
        return [
            {
                "code": row["organization__region"],
                "name": str(labels.get(row["organization__region"], row["organization__region"])),
                "total": row["total"],
                **{s: row[s] for s in STATUSES},
                "acceptance_rate": _pct(row["accepted"], row["total"]),
            }
            for row in rows
        ]

    # ================= UPCOMING DEADLINES =================
    def _upcoming(self):
        until = self.today + timedelta(days=UPCOMING_DAYS)
        qs = self._assignments().filter(deadline__deadline_at__gte=self.today, deadline__deadline_at__lte=until)
        rows = list(
            self._annotated_assignments(qs)
            .values("deadline_id", "deadline__deadline_at")
            .annotate(
                organizations=Count("id"),
                accepted=Count("id", filter=Q(acc_any=True)),
                submitted=Count("id", filter=Q(acc_any=True) | Q(sent_any=True)),
            )
            .order_by("deadline__deadline_at", "deadline_id")[:UPCOMING_LIMIT]
        )
        deadlines = Deadline.objects.select_related("statement", "statement__parent").in_bulk(
            [r["deadline_id"] for r in rows]
        )
        result = []
        for row in rows:
            deadline = deadlines[row["deadline_id"]]
            statement = deadline.statement
            result.append({
                "id": str(deadline.id),
                "statement_id": str(statement.id),
                "statement_name": get_translated_field(statement, "name", self.lang),
                "parent_name": get_translated_field(statement.parent, "name", self.lang),
                "submit_at": deadline.submit_at,
                "deadline_at": deadline.deadline_at.isoformat(),
                "days_left": (deadline.deadline_at - self.today).days,
                "organizations": row["organizations"],
                "submitted": row["submitted"],
                "accepted": row["accepted"],
            })
        return result
