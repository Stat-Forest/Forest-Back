"""
Tezlik: so'rovlar soni qatorlar soniga bog'liq bo'lmasligi kerak (N+1 yo'q).

Har test ikki xil hajmda bir xil endpoint'ni chaqiradi va DB so'rovlar soni
teng ekanini tekshiradi. Aniq sonlar emas — "N ga bog'liq emas" tekshiriladi,
shuning uchun kichik o'zgarishlar testni sindirmaydi.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.general.models import Organization
from apps.reports.models import Deadline, Report, Statement, StatementColumn

User = get_user_model()
S = Report.StatusChoices


class _Base(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        cls.dept = Statement.objects.create(name="Bo'lim Q", name_uz="Bo'lim Q", name_ru="Отдел Q")
        cls.super_admin = User.objects.create_user(
            email="super_q@example.com", password="TestPassword123!",
            first_name="Super", last_name="Admin", role="super_admin",
        )

    _seq = 0

    @classmethod
    def _form(cls, name=None):
        cls._seq += 1
        name = name or f"Shakl {cls._seq}"
        return Statement.objects.create(name=name, name_uz=name, name_ru=name, parent=cls.dept)

    @classmethod
    def _org(cls, region="tashkent"):
        cls._seq += 1
        return Organization.objects.create(name=f"Tashkilot {cls._seq}", region=region)

    @classmethod
    def _deadline(cls, form, submit_at, days, orgs=()):
        d = Deadline.objects.create(statement=form, submit_at=submit_at, deadline_at=cls.today + timedelta(days=days))
        if orgs:
            d.organizations.add(*orgs)
        return d

    @classmethod
    def _report(cls, org, form, deadline, status=S.ACCEPTED, **extra):
        extra.setdefault("region", org.region)
        return Report.objects.create(organization=org, statement=form, deadline=deadline, status=status, **extra)

    def _queries(self, url, user=None, **params):
        self.client.force_authenticate(user or self.super_admin)
        cache.clear()
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200, response.content)
        return len(ctx.captured_queries), response.json(), ctx.captured_queries


class LoginStatDeadlinesQueryTest(_Base):
    URL = "/api/v1/reports/login-stat-deadlines/"

    def _period(self, submit_at, n_forms=2, n_orgs=3, accepted=2):
        orgs = [self._org() for _ in range(n_orgs)]
        for _ in range(n_forms):
            form = self._form()
            d = self._deadline(form, submit_at, -5, orgs)
            for org in orgs[:accepted]:
                self._report(org, form, d)
        return orgs

    def test_query_count_does_not_grow_with_periods(self):
        self._period("2026-01")
        self.client.logout()
        cache.clear()
        with CaptureQueriesContext(connection) as a:
            r1 = self.client.get(self.URL)
        self.assertEqual(r1.status_code, 200)
        self._period("2026-02")
        self._period("2026-03")
        cache.clear()
        with CaptureQueriesContext(connection) as b:
            r2 = self.client.get(self.URL)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(r2.json()["results"]), 3)
        self.assertEqual(len(a.captured_queries), len(b.captured_queries),
                         "\n".join(q["sql"][:120] for q in b.captured_queries))

    def test_only_page_periods_are_loaded_and_orgs_are_not_prefetched(self):
        for m in range(1, 13):
            self._period(f"2025-{m:02d}", n_forms=1, n_orgs=2, accepted=1)
        cache.clear()
        with CaptureQueriesContext(connection) as ctx:
            r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["count"], 12)
        self.assertEqual(len(body["results"]), 10)
        self.assertEqual(body["results"][0]["submit_at"], "2025-12")
        self.assertEqual(body["results"][0]["total_organizations"], 2)
        self.assertEqual(body["results"][0]["submitted_organizations"], 1)
        prefetch = [q["sql"] for q in ctx.captured_queries if "_prefetch_related_val_deadline_id" in q["sql"]]
        self.assertEqual(prefetch, [], "tashkilotlar prefetch bilan to'liq yuklanmasligi kerak")
        deadline_selects = [q["sql"] for q in ctx.captured_queries
                            if 'FROM "reports_deadline"' in q["sql"] and '"reports_deadline"."submit_at" IN' in q["sql"]]
        self.assertTrue(deadline_selects, "muddatlar faqat sahifadagi davrlar uchun yuklanishi kerak")
        page2 = self.client.get(self.URL, {"page": 2}).json()
        self.assertEqual(len(page2["results"]), 2)

    def test_response_is_cached(self):
        self._period("2026-05")
        cache.clear()
        self.client.get(self.URL)
        with self.assertNumQueries(0):
            r = self.client.get(self.URL)
        self.assertEqual(len(r.json()["results"]), 1)

    def test_row_values(self):
        self._period("2026-01", n_forms=2, n_orgs=3, accepted=2)
        row = self.client.get(self.URL).json()["results"][0]
        self.assertEqual(row["total_organizations"], 3)
        self.assertEqual(row["submitted_organizations"], 2)
        self.assertEqual(row["pending_organizations"], 1)
        self.assertEqual(row["submission_percentage"], 66.67)


class ExpiredDeadlinesQueryTest(_Base):
    URL = "/api/v1/reports/expired-deadlines/"

    def _expired(self, n_deadlines, n_orgs):
        form = self._form()
        orgs = [self._org() for _ in range(n_orgs)]
        for i in range(n_deadlines):
            d = self._deadline(form, f"2025-{i + 1:02d}", -10 - i, orgs)
            self._report(orgs[0], form, d)  # birinchi tashkilot topshirgan
        return orgs

    def test_query_count_does_not_grow_with_deadlines_and_orgs(self):
        self._expired(1, 2)
        n1, data1, _ = self._queries(self.URL)
        self._expired(3, 4)
        n2, data2, qs = self._queries(self.URL)
        self.assertEqual(len(data2), 4)
        self.assertEqual(n1, n2, "\n".join(q["sql"][:120] for q in qs))

    def test_only_orgs_without_accepted_report_are_listed(self):
        orgs = self._expired(1, 3)
        _, data, _ = self._queries(self.URL)
        self.assertEqual(len(data), 1)
        listed = {o["id"] for o in data[0]["organizations"]}
        self.assertEqual(listed, {str(orgs[1].id), str(orgs[2].id)})


class DashboardStatsQueryTest(_Base):
    URL = "/api/v1/reports/dashboard/"

    def _expired(self, n_deadlines, n_orgs):
        form = self._form()
        orgs = [self._org() for _ in range(n_orgs)]
        for i in range(n_deadlines):
            d = self._deadline(form, f"2024-{i + 1:02d}", -10 - i, orgs)
            self._report(orgs[0], form, d)

    def test_query_count_does_not_grow(self):
        self._expired(1, 2)
        n1, _, _ = self._queries(self.URL)
        self._expired(3, 4)
        n2, data, qs = self._queries(self.URL)
        self.assertEqual(data["expired_deadlines"], 4)
        self.assertEqual(n1, n2, "\n".join(q["sql"][:120] for q in qs))

    def test_fully_submitted_deadline_is_not_expired(self):
        form = self._form()
        orgs = [self._org(), self._org()]
        d = self._deadline(form, "2024-05", -3, orgs)
        for org in orgs:
            self._report(org, form, d)
        _, data, _ = self._queries(self.URL)
        self.assertEqual(data["expired_deadlines"], 0)

    def test_cache_ttl_is_at_least_five_minutes(self):
        from apps.reports.views.dashboard import dashboard_stat_service as m
        self.assertGreaterEqual(m.DASHBOARD_CACHE_TTL, 300)


class StatementStatsQueryTest(_Base):
    URL = "/api/v1/reports/dashboard/statement-stats/"

    def _forms(self, n):
        for _ in range(n):
            form = self._form()
            org = self._org()
            d = self._deadline(form, "2026-04", 5, [org])
            self._report(org, form, d, status=S.SENT)
            self._report(org, form, d, status=S.SAVED, is_individual_general=True)

    def test_query_count_does_not_grow_with_statements(self):
        self._forms(1)
        n1, _, _ = self._queries(self.URL)
        self._forms(4)
        n2, data, qs = self._queries(self.URL)
        self.assertEqual(n1, n2, "\n".join(q["sql"][:120] for q in qs))
        self.assertEqual(data["totals"]["total"], 10)
        self.assertEqual(data["totals"]["sent"], 5)
        parent = data["data"][0]
        self.assertEqual(parent["count"], 5)
        self.assertEqual(parent["total"], 10)
        self.assertEqual(parent["children"][0]["total"], 2)


class UsersListQueryTest(_Base):
    URL = "/api/v1/reports/users/"

    def _users(self, n):
        org = self._org()
        for i in range(n):
            u = User.objects.create_user(
                email=f"u{self._seq}_{i}@example.com", password="TestPassword123!",
                first_name="A", last_name="B", role="hududiy_boshqarma",
            )
            u.region_user_orgs.add(org)

    def test_query_count_does_not_grow_with_users(self):
        root = User.objects.create_superuser(
            email="root_q@example.com", password="TestPassword123!", first_name="R", last_name="T",
        )
        self._users(1)
        n1, data1, _ = self._queries(self.URL, user=root)
        self._users(5)
        n2, data2, qs = self._queries(self.URL, user=root)
        self.assertEqual(data2["count"], data1["count"] + 5)
        self.assertEqual(n1, n2, "\n".join(q["sql"][:120] for q in qs))


class GeneralListQueryTest(_Base):
    """individual/regional/republic ro'yxatlari."""

    def _accepted(self, n, region="tashkent", submit_at="2026-06"):
        form = self._form()
        for _ in range(n):
            org = self._org(region)
            d = self._deadline(form, submit_at, 5, [org])
            self._report(org, form, d)
        return form

    def test_individual_list_does_not_build_filter_choices_from_reports(self):
        self._accepted(2)
        _, _, qs = self._queries("/api/v1/reports/individual/")
        joined = [q["sql"] for q in qs if "reports_statement" in q["sql"] and "reports_report" in q["sql"]
                  and "DISTINCT" in q["sql"]]
        self.assertEqual(joined, [], "filter choices lambda hali ham Report bilan join qilyapti")
        joined = [q["sql"] for q in qs if "reports_deadline" in q["sql"] and "reports_report" in q["sql"]
                  and "DISTINCT" in q["sql"]]
        self.assertEqual(joined, [])

    def test_individual_detail_fetches_object_once(self):
        self._accepted(1)
        report = Report.objects.get(is_individual_general=True)
        _, _, qs = self._queries(f"/api/v1/reports/individual/{report.id}/")
        main = [q for q in qs if '"reports_report"."id" =' in q["sql"] or "reports_report\".\"id\" = " in q["sql"]]
        self.assertLessEqual(len(main), 1, "\n".join(q["sql"][:150] for q in qs))

    def test_republic_list_query_count_does_not_grow(self):
        self._accepted(1, submit_at="2026-06")
        n1, _, _ = self._queries("/api/v1/reports/republic/")
        self._accepted(1, submit_at="2026-07")
        self._accepted(1, submit_at="2026-08")
        n2, data, qs = self._queries("/api/v1/reports/republic/")
        self.assertEqual(data["count"], 3)
        self.assertEqual(n1, n2, "\n".join(q["sql"][:120] for q in qs))


class ReportListQueryTest(_Base):
    def test_report_list_does_not_load_plants(self):
        form = self._form()
        org = self._org()
        d = self._deadline(form, "2026-09", 5, [org])
        self._report(org, form, d, status=S.SAVED)
        _, _, qs = self._queries("/api/v1/reports/")
        self.assertEqual([q["sql"] for q in qs if "reports_plant\"" in q["sql"]], [])

    def test_plant_report_list_loads_only_page_statements_columns(self):
        form = self._form()
        other = self._form()
        StatementColumn.objects.create(statement=other, title="X", ordering="1")
        org = self._org()
        d = self._deadline(form, "2026-09", 5, [org])
        self._report(org, form, d, status=S.SAVED, is_plant_based=True)
        _, _, qs = self._queries("/api/v1/reports/report-plant/")
        col_qs = [q["sql"] for q in qs if 'FROM "reports_statementcolumn"' in q["sql"]]
        self.assertTrue(col_qs)
        for sql in col_qs:
            self.assertRegex(sql, r'WHERE .*"reports_statementcolumn"\."statement_id" (IN|=)', sql)


class AuthQueryTest(_Base):
    def test_get_user_preloads_organization_and_statement(self):
        from apps.authentications.service.authentication import CustomJWTAuthentication
        org = self._org()
        user = User.objects.create_user(
            email="hodim_q@example.com", password="TestPassword123!", first_name="A", last_name="B",
            role="tashkilot_hodimi", organization=org, statement=self.dept,
        )
        token = RefreshToken.for_user(user).access_token
        loaded = CustomJWTAuthentication().get_user(token)
        with self.assertNumQueries(0):
            self.assertEqual(loaded.organization.id, org.id)
            self.assertEqual(loaded.statement.id, self.dept.id)


class FilterChoicesTest(_Base):
    def test_new_deadline_submit_at_is_accepted_by_report_filter(self):
        from apps.reports.filters.report_region import get_submit_at_choices
        form = self._form()
        self._deadline(form, "2030-01", 5)
        self.assertIn("2030-01", [v for v, _ in get_submit_at_choices()])
        self._deadline(form, "2031-01", 5)
        self.assertIn("2031-01", [v for v, _ in get_submit_at_choices()])


class IndexTest(_Base):
    def test_deadline_date_fields_are_indexed(self):
        indexed = {tuple(i.fields) for i in Deadline._meta.indexes}
        self.assertIn(("deadline_at",), indexed)
        self.assertIn(("submit_at",), indexed)

    def test_report_has_statement_deadline_status_index(self):
        indexed = {tuple(i.fields) for i in Report._meta.indexes}
        self.assertIn(("statement", "deadline", "status"), indexed)
        self.assertTrue(Report._meta.get_field("is_individual_general").db_index)
        self.assertTrue(Report._meta.get_field("is_republic").db_index)


class OrganizationCacheTest(_Base):
    def test_cache_timeout_is_useful(self):
        from apps.general.views.organization import OrganizationListAPIView
        self.assertGreaterEqual(OrganizationListAPIView.CACHE_TIMEOUT, 60)
