"""
Bosh sahifa hisobotlar statistikasi: GET /api/v1/reports/dashboard/overview/

Har bir rol faqat o'z doirasini ko'radi (scope_reports_for_user bilan bir xil):
tashkilot_hodimi — o'z tashkiloti, bolim_admin — o'z bo'limi, hududiy — o'z
hududi, super_admin — hammasi, billing rollari — faqat kadastr (endpoint esa
role_access allow-list bo'yicha ularga yopiq).
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
from apps.reports.models import Deadline, Report, Statement
from apps.reports.views.dashboard.dashboard_stat_service import DashboardStatService
from apps.reports.services.dashboard_overview import DashboardOverviewService

User = get_user_model()
URL = "/api/v1/reports/dashboard/overview/"

S = Report.StatusChoices


class DashboardOverviewTest(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()

        cls.dept_a = Statement.objects.create(name="Bo'lim A", name_uz="Bo'lim A", name_ru="Отдел A")
        cls.kadastr = Statement.objects.create(
            name="O‘rmon kadastri va monitoringi", name_uz="O‘rmon kadastri va monitoringi",
            name_ru="Лесной кадастр и мониторинг",
        )
        cls.form_a = Statement.objects.create(name="Shakl A", name_uz="Shakl A", name_ru="Форма A", parent=cls.dept_a)
        cls.form_k = Statement.objects.create(name="Kadastr shakli", name_uz="Kadastr shakli",
                                              name_ru="Кадастровая форма", parent=cls.kadastr)

        cls.org_a = Organization.objects.create(name="Tashkilot A", region="tashkent")
        cls.org_a2 = Organization.objects.create(name="Tashkilot A2", region="tashkent")
        cls.org_b = Organization.objects.create(name="Tashkilot B", region="namangan")

        # O'tgan muddat (10 kun oldin) — 3 tashkilotga, intizom hisobi uchun
        cls.past = Deadline.objects.create(statement=cls.form_a, submit_at="2026-09",
                                           deadline_at=cls.today - timedelta(days=10))
        cls.past.organizations.add(cls.org_a, cls.org_a2, cls.org_b)
        # Yaqinlashayotgan muddat (5 kun) — 2 tashkilotga
        cls.soon = Deadline.objects.create(statement=cls.form_k, submit_at="2026-10",
                                           deadline_at=cls.today + timedelta(days=5))
        cls.soon.organizations.add(cls.org_a, cls.org_b)
        # 30 kundan keyingi muddat — "yaqin" ro'yxatga tushmaydi
        cls.far = Deadline.objects.create(statement=cls.form_a, submit_at="2026-12",
                                          deadline_at=cls.today + timedelta(days=30))
        cls.far.organizations.add(cls.org_a)

        cls.hodim_a = cls._user("hodim_a", "tashkilot_hodimi", organization=cls.org_a)
        cls.bolim_a = cls._user("bolim_a", "bolim_admin", statement=cls.dept_a)
        cls.hudud_b = cls._user("hudud_b", "hududiy_boshqarma")
        cls.hudud_b.region_user_orgs.add(cls.org_b)
        cls.super_admin = cls._user("super", "super_admin")
        cls.billing_super = cls._user("bsuper", "billing_super")
        cls.billing_user = cls._user("buser", "billing_user", organization=cls.org_b)

    @classmethod
    def _user(cls, name, role, **extra):
        return User.objects.create_user(
            email=f"{name}@example.com", password="TestPassword123!",
            first_name="Test", last_name="User", role=role, **extra,
        )

    def setUp(self):
        cache.clear()
        mk = self._report
        # org_a (tashkent): past deadline — accepted on time; kadastr — sent
        self.r1 = mk(self.org_a, self.form_a, self.past, S.ACCEPTED, time_status=Report.TimeStatus.ON_TIME)
        self.r2 = mk(self.org_a, self.form_k, self.soon, S.SENT)
        # org_a2 (tashkent): past deadline — accepted late
        self.r3 = mk(self.org_a2, self.form_a, self.past, S.ACCEPTED, time_status=Report.TimeStatus.LATE)
        # org_b (namangan): past deadline — only saved (=> missing); kadastr — cancelled
        self.r4 = mk(self.org_b, self.form_a, self.past, S.SAVED)
        self.r5 = mk(self.org_b, self.form_k, self.soon, S.CANCELLED)
        # Umumiy (konsolidatsiya) hisobot statistikaga kirmaydi
        mk(self.org_b, self.form_a, self.far, S.ACCEPTED, is_report=False)

    def _report(self, org, statement, deadline, status, created_days_ago=1, **extra):
        report = Report.objects.create(organization=org, statement=statement, deadline=deadline, status=status, **extra)
        Report.objects.filter(pk=report.pk).update(created_at=timezone.now() - timedelta(days=created_days_ago))
        return report

    def _get(self, user, **params):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return self.client.get(URL, params)

    def _data(self, user, **params):
        response = self._get(user, **params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    # ---------------- access ----------------

    def test_anonymous_is_401(self):
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_billing_roles_are_blocked_by_role_allowlist(self):
        for user in (self.billing_user, self.billing_super):
            with self.subTest(role=user.role):
                self.assertEqual(self._get(user).status_code, 403)

    # ---------------- scoping ----------------

    def test_super_admin_sees_everything(self):
        data = self._data(self.super_admin)
        self.assertEqual(data["scope"]["level"], "all")
        kpis = data["kpis"]
        self.assertEqual(kpis["total"]["value"], 5)
        self.assertEqual(kpis["accepted"]["value"], 2)
        self.assertEqual(kpis["sent"]["value"], 1)
        self.assertEqual(kpis["saved"]["value"], 1)
        self.assertEqual(kpis["cancelled"]["value"], 1)
        self.assertEqual(kpis["accepted"]["share_pct"], 40.0)
        self.assertEqual(data["acceptance_rate"], 40.0)
        self.assertEqual({r["code"]: r["total"] for r in data["regions"]}, {"tashkent": 3, "namangan": 2})

    def test_tashkilot_hodimi_sees_only_own_organization(self):
        data = self._data(self.hodim_a)
        self.assertEqual(data["scope"]["level"], "organization")
        self.assertEqual(data["kpis"]["total"]["value"], 2)
        self.assertEqual(data["kpis"]["accepted"]["value"], 1)
        self.assertEqual(data["regions"], [])  # bitta hudud — bo'lim ko'rsatilmaydi
        self.assertEqual(sum(m["total"] for m in data["monthly"]), 2)
        self.assertEqual(data["discipline"]["total"], 1)
        self.assertEqual(data["discipline"]["on_time"], 1)
        upcoming = data["upcoming_deadlines"]
        self.assertEqual([u["id"] for u in upcoming], [str(self.soon.id)])
        self.assertEqual(upcoming[0]["organizations"], 1)
        self.assertEqual(upcoming[0]["submitted"], 1)

    def test_bolim_admin_sees_only_own_department(self):
        data = self._data(self.bolim_a)
        self.assertEqual(data["kpis"]["total"]["value"], 3)
        self.assertEqual([f["id"] for f in data["top_forms"]], [str(self.form_a.id)])
        self.assertEqual(data["upcoming_deadlines"], [])  # kadastr muddati boshqa bo'limniki

    def test_hududiy_sees_only_own_region(self):
        data = self._data(self.hudud_b)
        self.assertEqual(data["kpis"]["total"]["value"], 2)
        self.assertEqual(data["discipline"]["total"], 1)
        self.assertEqual(data["discipline"]["missing"], 1)

    def test_billing_service_scope_is_kadastr_only(self):
        """Endpoint billing'ga yopiq, lekin servis darajasida ham faqat kadastr (himoya qatlami)."""
        data = DashboardOverviewService(self.billing_super).build()
        self.assertEqual(data["scope"]["level"], "kadastr")
        self.assertEqual(data["kpis"]["total"]["value"], 2)
        self.assertEqual({f["id"] for f in data["top_forms"]}, {str(self.form_k.id)})
        self.assertEqual(data["discipline"]["total"], 0)

        data = DashboardOverviewService(self.billing_user).build()  # o'z tashkiloti (org_b)
        self.assertEqual(data["kpis"]["total"]["value"], 1)
        self.assertEqual(data["kpis"]["cancelled"]["value"], 1)

    def test_role_without_scope_gets_empty_stats(self):
        hodim = self._user("no_org", "tashkilot_hodimi")
        data = self._data(hodim)
        self.assertEqual(data["kpis"]["total"]["value"], 0)
        self.assertEqual(data["upcoming_deadlines"], [])
        self.assertEqual(data["discipline"]["total"], 0)

    # ---------------- calculations ----------------

    def test_deadline_discipline_matches_home_cards(self):
        """Bajarilgan / Muddatidan kech bajarilgan / Bajarilmagan — /reports/dashboard/ kartalari bilan bir xil."""
        disc = self._data(self.super_admin)["discipline"]
        self.assertEqual(
            {k: disc[k] for k in ("total", "on_time", "late", "missing")},
            {"total": 3, "on_time": 1, "late": 1, "missing": 1},
        )
        self.assertEqual(disc["on_time_rate"], 50.0)
        self.assertEqual(disc["completion_rate"], 66.7)

        cards = DashboardStatService(self.super_admin)._calculate_stats()
        self.assertEqual(
            (disc["on_time"], disc["late"], disc["missing"]),
            (cards["on_time_reports"], cards["late_reports"], cards["expired_deadlines"]),
        )
        kpis = self._data(self.super_admin)["kpis"]
        self.assertEqual(
            (kpis["sent"]["value"], kpis["cancelled"]["value"], kpis["accepted"]["value"], kpis["saved"]["value"]),
            (cards["sent_reports"], cards["returned_reports"], cards["accepted_reports"], cards["draft_reports"]),
        )

    def test_monthly_trend_has_12_months_and_buckets_by_created_month(self):
        Report.objects.filter(pk=self.r1.pk).update(created_at=timezone.now() - timedelta(days=100))
        monthly = self._data(self.super_admin)["monthly"]
        self.assertEqual(len(monthly), 12)
        self.assertEqual(monthly[-1]["month"], self.today.strftime("%Y-%m"))
        self.assertEqual(sum(m["total"] for m in monthly), 5)
        self.assertEqual(sum(m["accepted"] for m in monthly), 2)

    def test_kpi_trend_against_previous_period(self):
        # Oldingi 30 kunlik oynada 1 ta hisobot -> joriy 5 ta: +400%
        self._report(self.org_b, self.form_k, self.far, S.SAVED, created_days_ago=45)
        kpis = self._data(self.super_admin, period="month")["kpis"]
        self.assertEqual(kpis["total"]["value"], 5)
        self.assertEqual(kpis["total"]["previous"], 1)
        self.assertEqual(kpis["total"]["change_pct"], 400.0)
        self.assertIsNone(kpis["accepted"]["change_pct"])  # oldingi 0 — foiz yo'q

        data = self._data(self.super_admin, period="all")
        self.assertEqual(data["kpis"]["total"]["value"], 6)
        self.assertIsNone(data["kpis"]["total"]["change_pct"])
        self.assertIsNone(data["period_start"])

    def test_default_and_invalid_period_is_all_time(self):
        self.assertEqual(self._data(self.super_admin)["period"], "all")
        self.assertEqual(self._data(self.super_admin, period="bogus")["period"], "all")

    def test_statement_names_follow_lang(self):
        data = self._data(self.super_admin, lang="ru")
        names = {f["name"] for f in data["top_forms"]}
        self.assertEqual(names, {"Форма A", "Кадастровая форма"})
        soon = data["upcoming_deadlines"][0]
        self.assertEqual(soon["statement_name"], "Кадастровая форма")
        self.assertEqual(soon["parent_name"], "Лесной кадастр и мониторинг")
        self.assertEqual(soon["days_left"], 5)
        self.assertEqual((soon["organizations"], soon["submitted"], soon["accepted"]), (2, 1, 0))

    def test_result_is_cached_per_scope(self):
        self._data(self.super_admin)
        # Kesh ishlatiladi: ikkinchi so'rovda hisobot jadvaliga murojaat yo'q
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self._data(self.super_admin)["kpis"]["total"]["value"], 5)
        self.assertEqual([q for q in ctx.captured_queries if '"reports_report"' in q["sql"]], [])
        # Hisobot saqlanganda kesh versiyasi oshadi — yangi qiymat ko'rinadi
        self._report(self.org_a, self.form_a, self.far, S.SAVED)
        self.assertEqual(self._data(self.super_admin)["kpis"]["total"]["value"], 6)
        # boshqa doira — alohida kalit
        self.assertEqual(self._data(self.hodim_a)["kpis"]["total"]["value"], 3)
