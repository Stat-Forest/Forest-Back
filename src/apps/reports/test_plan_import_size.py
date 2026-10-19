"""Audit B15: reja Excel importi hajm chegarasi — katta fayl xotirani to'ldirmasin."""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.reports.models import Statement

User = get_user_model()


class PlanImportSizeCapTest(APITestCase):
    def test_oversized_file_is_rejected_before_parsing(self):
        dept = Statement.objects.create(name="Bo'lim")
        stmt = Statement.objects.create(name="Shakl", parent=dept)
        bolim = User.objects.create_user(email="b@example.com", password="TestPassword123!",
                                         first_name="T", last_name="U", role="bolim_admin", statement=dept)
        self.client.force_authenticate(bolim)
        big = SimpleUploadedFile("plan.xlsx", b"PK\x03\x04" + b"0" * (6 * 1024 * 1024),
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp = self.client.post(
            f"/api/v1/reports/plan-excel/import/?organization=00000000-0000-0000-0000-000000000001&statement={stmt.id}&year=2026",
            {"file": big}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("MB", resp.content.decode())
