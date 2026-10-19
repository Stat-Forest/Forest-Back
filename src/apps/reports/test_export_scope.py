import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.reports.models import Deadline, Report, Statement

User = get_user_model()

URL = "/api/v1/reports/export-excel/"


class ReportExportScopeTest(APITestCase):
    """
    Excel eksport ham ro'yxat/detail kabi foydalanuvchi ko'lamiga bo'ysunishi kerak:
    boshqa tashkilot hisobotining UUID'i bilan eksport qilib bo'lmaydi (audit A3).
    """

    @classmethod
    def setUpTestData(cls):
        dept = Statement.objects.create(name="Bo'lim")
        cls.stmt = Statement.objects.create(name="Shakl", parent=dept)
        cls.org_a = Organization.objects.create(name="Tashkilot A", region="tashkent")
        cls.org_b = Organization.objects.create(name="Tashkilot B", region="namangan")
        cls.deadline = Deadline.objects.create(statement=cls.stmt, submit_at="2026")
        cls.hodim_a = User.objects.create_user(
            email="hodim_a@example.com", password="TestPassword123!",
            first_name="T", last_name="U", role="tashkilot_hodimi", organization=cls.org_a,
        )
        cls.support = User.objects.create_user(
            email="support@example.com", password="TestPassword123!",
            first_name="T", last_name="U", role="support_admin",
        )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.override = override_settings(EXPORT_ROOT=os.path.join(self.tmp.name, "exports"))
        self.override.enable()
        self.report_a = Report.objects.create(organization=self.org_a, statement=self.stmt, deadline=self.deadline)
        self.report_b = Report.objects.create(organization=self.org_b, statement=self.stmt, deadline=self.deadline)

    def tearDown(self):
        self.override.disable()
        self.tmp.cleanup()

    def _export(self, user, report):
        self.client.force_authenticate(user)
        return self.client.get(URL, {"ids": str(report.id), "mode": "json"})

    def test_hodim_cannot_export_other_organization_report(self):
        self.assertEqual(self._export(self.hodim_a, self.report_b).status_code, 404)

    def test_hodim_can_export_own_report(self):
        self.assertEqual(self._export(self.hodim_a, self.report_a).status_code, 200)

    def test_export_error_response_does_not_leak_exception_text(self):
        self.client.force_authenticate(self.hodim_a)
        resp = self.client.get(URL, {"ids": "not-a-uuid", "mode": "json"})
        self.assertNotIn("error", resp.json())
