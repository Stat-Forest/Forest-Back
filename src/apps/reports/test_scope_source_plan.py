"""Audit B8: per-tashkilot endpointlar (manba hisobotlar, reja qiymatlari) foydalanuvchi ko'lamiga bo'ysunadi."""
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.reports.models import Deadline, Plan, PlanItem, Report, Statement, StatementColumn

User = get_user_model()
SOURCE_URL = "/api/v1/reports/source-reports/kochat-nihol/"
PLAN_URL = "/api/v1/reports/plan-items/"


class SourceAndPlanScopeTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        dept = Statement.objects.create(name="Bo'lim")
        cls.stmt = Statement.objects.create(name="Ko‘chat va Nihol", parent=dept)
        cls.column = StatementColumn.objects.create(statement=cls.stmt, title="1", title_uz="1", title_ru="1", ordering="1")
        cls.org_a = Organization.objects.create(name="Tashkilot A", region="tashkent")
        cls.org_b = Organization.objects.create(name="Tashkilot B", region="namangan")
        cls.deadline = Deadline.objects.create(statement=cls.stmt, submit_at="2026")
        for org in (cls.org_a, cls.org_b):
            Report.objects.create(organization=org, statement=cls.stmt, deadline=cls.deadline,
                                  status=Report.StatusChoices.ACCEPTED)
            plan = Plan.objects.create(statement=cls.stmt, organization=org, year=2026)
            PlanItem.objects.create(plan=plan, column=cls.column, plan_value="5")
        cls.hodim_a = User.objects.create_user(
            email="hodim_a@example.com", password="TestPassword123!", first_name="T", last_name="U",
            role="tashkilot_hodimi", organization=cls.org_a,
        )
        cls.rahbariyat = User.objects.create_user(
            email="rahbariyat@example.com", password="TestPassword123!", first_name="T", last_name="U",
            role="rahbariyat",
        )

    def _items(self, resp):
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        return data["results"] if isinstance(data, dict) and "results" in data else data

    def test_source_reports_are_scoped_to_user_organization(self):
        self.client.force_authenticate(self.hodim_a)
        self.assertEqual(self._items(self.client.get(SOURCE_URL, {"organization": str(self.org_b.id)})), [])
        orgs = {row["organization"] if isinstance(row.get("organization"), str) else row["organization"]["id"]
                for row in self._items(self.client.get(SOURCE_URL))}
        self.assertEqual(orgs, {str(self.org_a.id)})

    def test_plan_items_of_other_organization_are_hidden(self):
        self.client.force_authenticate(self.hodim_a)
        params = {"statement": str(self.stmt.id), "year": 2026}
        self.assertEqual(self._items(self.client.get(PLAN_URL, {**params, "organization": str(self.org_b.id)})), [])
        self.assertEqual(len(self._items(self.client.get(PLAN_URL, {**params, "organization": str(self.org_a.id)}))), 1)

    def test_rahbariyat_sees_everything(self):
        self.client.force_authenticate(self.rahbariyat)
        self.assertEqual(len(self._items(self.client.get(SOURCE_URL))), 2)
        params = {"statement": str(self.stmt.id), "year": 2026, "organization": str(self.org_b.id)}
        self.assertEqual(len(self._items(self.client.get(PLAN_URL, params))), 1)
