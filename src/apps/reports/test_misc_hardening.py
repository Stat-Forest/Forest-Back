"""Audit C5 (cache kalitlari), C6 (eksport fayllari), C7 (admin escape), C13 (ko'chat hisobot o'chirish), C16 (TIN maskasi)."""
import os
import tempfile
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, override_settings
from rest_framework.test import APITestCase

from apps.base.admin import admin_site
from apps.general.models import Organization
from apps.reports.admin.deadline import DeadlineAdmin
from apps.reports.models import Deadline, Report, ReportItem, ReportSignature, Statement, StatementColumn
from apps.reports.serializers.plant.plant_report_delete import PlantReportDeleteSerializer
from apps.reports.services import report_signing
from apps.reports.test_report_signing import TIN, PINFL, FakeEimzo, fake_sign

User = get_user_model()


def make_user(name, role, **extra):
    return User.objects.create_user(email=f"{name}@example.com", password="TestPassword123!",
                                    first_name="T", last_name="U", role=role, **extra)


class LoginStatDeadlinesCacheKeyTest(APITestCase):
    def test_unknown_query_params_do_not_create_cache_keys(self):
        cache.clear()
        self.assertEqual(self.client.get("/api/v1/reports/login-stat-deadlines/", {"junk": "abc123xyz"}).status_code, 200)
        self.assertEqual([k for k in cache.keys("login_stat_deadlines:*") if "abc123xyz" in k], [])


class ExportRetentionTest(APITestCase):
    def test_old_export_files_are_purged_on_new_export(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        export_dir = os.path.join(tmp.name, "exports")
        os.makedirs(export_dir)
        old = os.path.join(export_dir, "eski_2026-01-01_10-00_20260101_100000.xlsx")
        with open(old, "wb") as f:
            f.write(b"x")
        two_days_ago = time.time() - 2 * 24 * 3600
        os.utime(old, (two_days_ago, two_days_ago))

        dept = Statement.objects.create(name="Bo'lim")
        stmt = Statement.objects.create(name="Shakl", parent=dept)
        org = Organization.objects.create(name="T", region="tashkent")
        deadline = Deadline.objects.create(statement=stmt, submit_at="2026")
        report = Report.objects.create(organization=org, statement=stmt, deadline=deadline)
        self.client.force_authenticate(make_user("hodim", "tashkilot_hodimi", organization=org))
        with override_settings(EXPORT_ROOT=export_dir):
            resp = self.client.get("/api/v1/reports/export-excel/", {"ids": str(report.id), "mode": "json"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(os.path.exists(old))
        self.assertEqual(len([f for f in os.listdir(export_dir) if f.endswith(".xlsx")]), 1)


class DeadlineAdminEscapeTest(APITestCase):
    def test_organization_name_is_html_escaped(self):
        dept = Statement.objects.create(name="Bo'lim")
        stmt = Statement.objects.create(name="Shakl", parent=dept)
        deadline = Deadline.objects.create(statement=stmt, submit_at="2026")
        org = Organization.objects.create(name="<script>alert(1)</script>", region="tashkent")
        deadline.organizations.add(org)
        html = str(DeadlineAdmin(Deadline, admin_site).organizations_display(deadline))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class PlantReportDeleteOwnershipTest(APITestCase):
    def setUp(self):
        dept = Statement.objects.create(name="Bo'lim")
        self.stmt = Statement.objects.create(name="Shakl", parent=dept, use_plant_plan=True)
        self.org = Organization.objects.create(name="T", region="tashkent")
        deadline = Deadline.objects.create(statement=self.stmt, submit_at="2026")
        self.owner = make_user("owner", "tashkilot_hodimi", organization=self.org)
        self.colleague = make_user("colleague", "tashkilot_hodimi", organization=self.org)
        self.report = Report.objects.create(organization=self.org, statement=self.stmt, deadline=deadline,
                                            created_by=self.owner, is_plant_based=True)

    def _valid(self, user):
        request = RequestFactory().post("/")
        request.user = user
        return PlantReportDeleteSerializer(data={"report_id": str(self.report.id)}, context={"request": request}).is_valid()

    def test_colleague_cannot_delete_someone_elses_draft(self):
        self.assertFalse(self._valid(self.colleague))

    def test_creator_can_delete_own_draft(self):
        self.assertTrue(self._valid(self.owner))


class VerifyPageMasksTinTest(APITestCase):
    def test_public_verify_masks_signer_tin(self):
        cache.clear()
        dept = Statement.objects.create(name="Bo'lim")
        stmt = Statement.objects.create(name="Shakl", parent=dept)
        org = Organization.objects.create(name="T", region="tashkent", stir=int(TIN))
        deadline = Deadline.objects.create(statement=stmt, submit_at="2026")
        column = StatementColumn.objects.create(statement=stmt, title="Amalda", ordering="1")
        rahbar = make_user("rahbar", "tashkilot_rahbari", organization=org, pinfl=PINFL)
        report = Report.objects.create(organization=org, statement=stmt, deadline=deadline)
        ReportItem.objects.create(report=report, statement_column=column, value="10")
        with patch.object(report_signing, "eimzo_api", FakeEimzo()):
            document, _nonce = report_signing.build_signing_document(report, rahbar)
            sig = report_signing.verify_and_store_signature(report=report, user=rahbar, pkcs7=fake_sign(document), request=None)
        body = self.client.get(f"/api/v1/reports/signatures/{sig.id}/verify/").json()
        self.assertNotEqual(body["signer"].get("tin"), TIN)
        self.assertNotIn(TIN, str(body))
