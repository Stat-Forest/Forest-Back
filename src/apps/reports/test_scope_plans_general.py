from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.reports.models import Deadline, Plan, Report, Statement

User = get_user_model()
BASE = "/api/v1/reports"


class ScopeFixtures(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept_a = Statement.objects.create(name="Bo'lim A")
        cls.dept_b = Statement.objects.create(name="Bo'lim B")
        cls.stmt_a = Statement.objects.create(name="Shakl A", parent=cls.dept_a)
        cls.stmt_b = Statement.objects.create(name="Shakl B", parent=cls.dept_b)
        cls.org_a = Organization.objects.create(name="Tashkilot A", region="tashkent")
        cls.org_b = Organization.objects.create(name="Tashkilot B", region="namangan")
        cls.deadline_a = Deadline.objects.create(statement=cls.stmt_a, submit_at="2026")
        cls.hodim_a = cls._user("hodim_a", "tashkilot_hodimi", organization=cls.org_a)
        cls.bolim_a = cls._user("bolim_a", "bolim_admin", statement=cls.dept_a)
        cls.bolim_b = cls._user("bolim_b", "bolim_admin", statement=cls.dept_b)
        cls.hudud_a = cls._user("hudud_a", "hududiy_boshqarma")
        cls.hudud_a.region_user_orgs.add(cls.org_a)
        cls.rahbariyat = cls._user("rahbariyat", "rahbariyat")
        cls.support = cls._user("support", "support_admin")

    @classmethod
    def _user(cls, name, role, **extra):
        return User.objects.create_user(
            email=f"{name}@example.com", password="TestPassword123!",
            first_name="T", last_name="U", role=role, **extra,
        )

    def _get(self, user, url):
        self.client.force_authenticate(user)
        return self.client.get(url)

    def _ids(self, resp):
        data = resp.json()
        rows = data.get("results", data)
        return {r["id"] for r in rows}


class PlanScopeTest(ScopeFixtures):
    def setUp(self):
        self.plan_a = Plan.objects.create(statement=self.stmt_a, organization=self.org_a, year=2026)
        self.plan_b = Plan.objects.create(statement=self.stmt_b, organization=self.org_b, year=2026)

    def test_retrieve_scope(self):
        cases = {
            self.hodim_a: (200, 404),
            self.bolim_a: (200, 404),
            self.bolim_b: (404, 200),
            self.hudud_a: (200, 404),
            self.rahbariyat: (200, 200),
            self.support: (404, 404),
        }
        for user, (a, b) in cases.items():
            with self.subTest(role=user.role):
                self.assertEqual(self._get(user, f"{BASE}/plan/{self.plan_a.id}/").status_code, a)
                self.assertEqual(self._get(user, f"{BASE}/plan/{self.plan_b.id}/").status_code, b)

    def test_list_scope(self):
        self.assertEqual(self._ids(self._get(self.bolim_a, f"{BASE}/plan-list/")), {str(self.plan_a.id)})
        self.assertEqual(self._ids(self._get(self.hodim_a, f"{BASE}/plan-list/")), {str(self.plan_a.id)})
        self.assertEqual(self._ids(self._get(self.rahbariyat, f"{BASE}/plan-list/")), {str(self.plan_a.id), str(self.plan_b.id)})
        self.assertEqual(self._ids(self._get(self.support, f"{BASE}/plan-list/")), set())

    def test_other_department_admin_cannot_update_or_delete(self):
        self.client.force_authenticate(self.bolim_b)
        self.assertEqual(self.client.patch(f"{BASE}/plan/{self.plan_a.id}/update/", {"year": 2027}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"{BASE}/plans/{self.plan_a.id}/delete/").status_code, 404)
        self.assertTrue(Plan.objects.filter(id=self.plan_a.id, year=2026).exists())

    def test_own_department_admin_can_delete(self):
        self.client.force_authenticate(self.bolim_a)
        self.assertEqual(self.client.delete(f"{BASE}/plans/{self.plan_a.id}/delete/").status_code, 204)
        self.assertFalse(Plan.objects.filter(id=self.plan_a.id).exists())


class GeneralReportScopeTest(ScopeFixtures):
    def setUp(self):
        self.reg_tash = Report.objects.create(statement=self.stmt_a, deadline=self.deadline_a, is_general=True, region="tashkent")
        self.reg_nam = Report.objects.create(statement=self.stmt_a, deadline=self.deadline_a, is_general=True, region="namangan")
        self.ind_a = Report.objects.create(statement=self.stmt_a, deadline=self.deadline_a, organization=self.org_a, is_individual_general=True)
        self.ind_b = Report.objects.create(statement=self.stmt_b, deadline=self.deadline_a, organization=self.org_b, is_individual_general=True)

    def test_regional_scope(self):
        self.assertEqual(self._ids(self._get(self.hodim_a, f"{BASE}/regional/")), {str(self.reg_tash.id)})
        self.assertEqual(self._ids(self._get(self.hudud_a, f"{BASE}/regional/")), {str(self.reg_tash.id)})
        self.assertEqual(self._ids(self._get(self.rahbariyat, f"{BASE}/regional/")), {str(self.reg_tash.id), str(self.reg_nam.id)})
        self.assertEqual(self._ids(self._get(self.support, f"{BASE}/regional/")), set())
        self.assertEqual(self._get(self.hodim_a, f"{BASE}/regional/{self.reg_nam.id}/").status_code, 404)
        self.assertEqual(self._get(self.hodim_a, f"{BASE}/regional/{self.reg_tash.id}/").status_code, 200)

    def test_individual_scope(self):
        self.assertEqual(self._ids(self._get(self.hodim_a, f"{BASE}/individual/")), {str(self.ind_a.id)})
        self.assertEqual(self._ids(self._get(self.bolim_a, f"{BASE}/individual/")), {str(self.ind_a.id)})
        self.assertEqual(self._get(self.hodim_a, f"{BASE}/individual/{self.ind_b.id}/").status_code, 404)
        self.assertEqual(self._get(self.hodim_a, f"{BASE}/individual/{self.ind_a.id}/").status_code, 200)
        self.assertEqual(self._get(self.rahbariyat, f"{BASE}/individual/{self.ind_b.id}/").status_code, 200)
