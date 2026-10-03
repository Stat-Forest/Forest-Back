from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.reports.models import Deadline, Report, Statement
from apps.reports.permissions.report_scope import scope_reports_for_user

User = get_user_model()

BASE = "/api/v1/reports"


class ReportAccessTest(APITestCase):
    """
    Foydalanuvchi faqat o'z doirasidagi (tashkilot / bo'lim / hudud)
    hisobotlarga murojaat qila olishi kerak.
    """

    @classmethod
    def setUpTestData(cls):
        cls.dept_a = Statement.objects.create(name="Bo'lim A")
        cls.dept_b = Statement.objects.create(name="Bo'lim B")
        cls.stmt_a = Statement.objects.create(name="Shakl A", parent=cls.dept_a)
        cls.stmt_b = Statement.objects.create(name="Shakl B", parent=cls.dept_b)

        cls.org_a = Organization.objects.create(name="Tashkilot A", region="tashkent")
        cls.org_b = Organization.objects.create(name="Tashkilot B", region="namangan")

        cls.deadline_a = Deadline.objects.create(statement=cls.stmt_a, submit_at="2026")
        cls.deadline_b = Deadline.objects.create(statement=cls.stmt_b, submit_at="2026")

        cls.hodim_a = cls._user("hodim_a", "tashkilot_hodimi", organization=cls.org_a)
        cls.rahbar_a = cls._user("rahbar_a", "tashkilot_rahbari", organization=cls.org_a)
        cls.bolim_a = cls._user("bolim_a", "bolim_admin", statement=cls.dept_a)
        cls.hudud_a = cls._user("hudud_a", "hududiy_boshqarma")
        cls.hudud_a.region_user_orgs.add(cls.org_a)
        cls.rahbariyat = cls._user("rahbariyat", "rahbariyat")
        cls.support = cls._user("support", "support_admin")

    @classmethod
    def _user(cls, name, role, **extra):
        return User.objects.create_user(
            email=f"{name}@example.com",
            password="TestPassword123!",
            first_name="Test",
            last_name="User",
            role=role,
            **extra,
        )

    def setUp(self):
        self.report_a = Report.objects.create(
            organization=self.org_a, statement=self.stmt_a, deadline=self.deadline_a
        )
        self.report_b = Report.objects.create(
            organization=self.org_b, statement=self.stmt_b, deadline=self.deadline_b
        )

    def _as(self, user):
        self.client.force_authenticate(user)
        return self.client

    # ---------------- scope_reports_for_user ----------------

    def test_scope_by_role(self):
        expected = {
            self.hodim_a: {self.report_a},
            self.rahbar_a: {self.report_a},
            self.bolim_a: {self.report_a},
            self.hudud_a: {self.report_a},
            self.rahbariyat: {self.report_a, self.report_b},
            self.support: set(),
        }
        for user, reports in expected.items():
            with self.subTest(role=user.role):
                scoped = scope_reports_for_user(Report.objects.all(), user)
                self.assertEqual(set(scoped), reports)

    def test_scope_without_organization_or_statement_is_empty(self):
        hodim = self._user("no_org", "tashkilot_hodimi")
        bolim = self._user("no_stmt", "bolim_admin")
        self.assertFalse(scope_reports_for_user(Report.objects.all(), hodim).exists())
        self.assertFalse(scope_reports_for_user(Report.objects.all(), bolim).exists())

    # ---------------- retrieve / update ----------------

    def test_retrieve_foreign_report_is_404(self):
        response = self._as(self.hodim_a).get(f"{BASE}/{self.report_b.id}/")
        self.assertEqual(response.status_code, 404)

    def test_retrieve_own_report_is_200(self):
        response = self._as(self.hodim_a).get(f"{BASE}/{self.report_a.id}/")
        self.assertEqual(response.status_code, 200)

    def test_update_foreign_report_is_404(self):
        response = self._as(self.hodim_a).patch(
            f"{BASE}/{self.report_b.id}/update/", {"report_items": []}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_update_accepted_report_is_forbidden(self):
        Report.objects.filter(id=self.report_a.id).update(status=Report.StatusChoices.ACCEPTED)
        response = self._as(self.hodim_a).patch(
            f"{BASE}/{self.report_a.id}/update/", {"report_items": []}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_update_by_non_editor_role_is_forbidden(self):
        response = self._as(self.bolim_a).patch(
            f"{BASE}/{self.report_a.id}/update/", {"report_items": []}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_update_own_saved_report_is_allowed(self):
        response = self._as(self.hodim_a).patch(
            f"{BASE}/{self.report_a.id}/update/", {"report_items": []}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    # ---------------- status transitions ----------------

    def test_send_foreign_report_is_rejected(self):
        response = self._as(self.rahbar_a).post(
            f"{BASE}/send/", {"id": str(self.report_b.id)}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.report_b.refresh_from_db()
        self.assertEqual(self.report_b.status, Report.StatusChoices.SAVED)

    def test_accept_report_of_other_department_is_rejected(self):
        Report.objects.filter(id=self.report_b.id).update(status=Report.StatusChoices.SENT)
        response = self._as(self.bolim_a).post(
            f"{BASE}/accept/", {"id": str(self.report_b.id)}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.report_b.refresh_from_db()
        self.assertEqual(self.report_b.status, Report.StatusChoices.SENT)

    def test_accept_own_department_report(self):
        Report.objects.filter(id=self.report_a.id).update(status=Report.StatusChoices.SENT)
        response = self._as(self.bolim_a).post(
            f"{BASE}/accept/", {"id": str(self.report_a.id)}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.report_a.refresh_from_db()
        self.assertEqual(self.report_a.status, Report.StatusChoices.ACCEPTED)

    def test_cancel_report_of_other_department_is_rejected(self):
        Report.objects.filter(id=self.report_b.id).update(status=Report.StatusChoices.SENT)
        response = self._as(self.bolim_a).post(
            f"{BASE}/cancel/",
            {"id": str(self.report_b.id), "cancel_reason": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    # ---------------- report items ----------------

    def test_report_items_only_from_own_reports(self):
        response = self._as(self.support).get(f"{BASE}/report-items/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
