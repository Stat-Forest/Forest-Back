"""
Chuqur xavfsizlik auditi (2026-10-27) — hisobotlar: tashkilot body'dan olinmasin
(N1/N2), plant-hisobot update holati (N3), reja statement egaligi (N5), plant
svodka doirasi (N6), report-items (N9), muddatlar (N16), import-parse (N8),
noto'g'ri UUID (N14), Excel zip bomb (R1).
"""
import io
import zipfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.reports.models import Deadline, Plant, Report, ReportItem, ReportItemInner, Statement, StatementColumn
from apps.utils.excel_safety import UnsafeExcelFile, check_xlsx_zip

User = get_user_model()
BASE = "/api/v1/reports"


def zip_bomb(entry_size=40 * 1024 * 1024) -> bytes:
    """Kichik, lekin yoyilganda katta .xlsx ko'rinishidagi ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/worksheets/sheet1.xml", b"0" * entry_size)
    return buf.getvalue()


class Security2Base(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept_a = Statement.objects.create(name="Bo'lim A", name_uz="Bo'lim A")
        cls.dept_b = Statement.objects.create(name="Bo'lim B", name_uz="Bo'lim B")
        cls.stmt_a = Statement.objects.create(name="Shakl A", name_uz="Shakl A", parent=cls.dept_a, period="yearly")
        cls.stmt_b = Statement.objects.create(name="Shakl B", name_uz="Shakl B", parent=cls.dept_b, period="yearly")
        cls.c_org = StatementColumn.objects.create(statement=cls.stmt_a, title="Tashkilot nomi", title_uz="Tashkilot nomi",
                                                   ordering="1.1", is_organization=True)
        cls.c_val = StatementColumn.objects.create(statement=cls.stmt_a, title="Maydon", title_uz="Maydon", ordering="1.2")
        cls.org_a = Organization.objects.create(name="Tashkilot A", name_uz="Tashkilot A", region="tashkent")
        cls.org_b = Organization.objects.create(name="Tashkilot B", name_uz="Tashkilot B", region="namangan")
        cls.deadline_a = Deadline.objects.create(statement=cls.stmt_a, submit_at="2025")
        cls.deadline_a.organizations.add(cls.org_a, cls.org_b)
        cls.hodim_a = cls._user("hodim_a", "tashkilot_hodimi", organization=cls.org_a)
        cls.rahbar_a = cls._user("rahbar_a", "tashkilot_rahbari", organization=cls.org_a)
        cls.bolim_a = cls._user("bolim_a", "bolim_admin", statement=cls.dept_a)
        cls.rahbariyat = cls._user("rahbariyat", "rahbariyat")

    @classmethod
    def _user(cls, name, role, **extra):
        return User.objects.create_user(email=f"{name}@example.com", password="TestPassword123!",
                                        first_name="Test", last_name="User", role=role, **extra)

    def _as(self, user):
        self.client.force_authenticate(user)
        return self.client


class ReportCreateOrganizationTest(Security2Base):
    def _payload(self, org):
        return {
            "deadline": str(self.deadline_a.id),
            "report_items": [
                {"statement_column": str(self.c_org.id), "inners": [{"value": str(org.id)}]},
                {"statement_column": str(self.c_val.id), "inners": [{"value": "12.5"}]},
            ],
        }

    def test_report_for_other_organization_is_rejected(self):
        resp = self._as(self.hodim_a).post(f"{BASE}/create/", self._payload(self.org_b), format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(Report.objects.filter(organization=self.org_b).exists())

    def test_report_for_own_organization_is_created(self):
        resp = self._as(self.hodim_a).post(f"{BASE}/create/", self._payload(self.org_a), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(Report.objects.filter(organization=self.org_a, statement=self.stmt_a).exists())

    def test_plant_report_for_other_organization_is_rejected(self):
        resp = self._as(self.hodim_a).post(f"{BASE}/plant/create/", self._payload(self.org_b), format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("o'z tashkilotingiz", resp.content.decode())
        self.assertFalse(Report.objects.filter(organization=self.org_b).exists())

    def test_plant_report_create_requires_creator_role(self):
        # Oddiy hisobot bilan bir xil: rahbar yaratmaydi (CanCreateReport)
        resp = self._as(self.rahbar_a).post(f"{BASE}/plant/create/", self._payload(self.org_a), format="json")
        self.assertEqual(resp.status_code, 403)


class PlantReportUpdateStatusTest(Security2Base):
    def setUp(self):
        self.accepted = Report.objects.create(organization=self.org_a, statement=self.stmt_a, deadline=self.deadline_a,
                                              is_plant_based=True, status="accepted", region="tashkent")
        self.saved = Report.objects.create(organization=self.org_a, statement=self.stmt_a, deadline=self.deadline_a,
                                           is_plant_based=True, status="saved", region="tashkent")

    def test_accepted_plant_report_cannot_be_edited(self):
        body = {"report_items": [{"statement_column": str(self.c_val.id), "inners": [{"value": "0"}]}]}
        resp = self._as(self.hodim_a).put(f"{BASE}/report-plant/{self.accepted.id}/update", body, format="json")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertFalse(ReportItemInner.objects.filter(report_item__report=self.accepted).exists())

    def test_rahbar_cannot_edit_plant_report(self):
        body = {"report_items": [{"statement_column": str(self.c_val.id), "inners": [{"value": "1"}]}]}
        resp = self._as(self.rahbar_a).put(f"{BASE}/report-plant/{self.saved.id}/update", body, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_saved_plant_report_is_still_editable_by_hodim(self):
        plant = Plant.objects.create(name="Terak", statement=self.stmt_a)
        body = {"deadline": str(self.deadline_a.id),
                "report_items": [{"statement_column": str(self.c_val.id), "inners": [{"plant": str(plant.id), "value": "1"}]}]}
        resp = self._as(self.hodim_a).put(f"{BASE}/report-plant/{self.saved.id}/update", body, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_get_still_works(self):
        self.assertEqual(self._as(self.hodim_a).get(f"{BASE}/report-plant/{self.accepted.id}/update").status_code, 200)


class PlanCreateStatementOwnershipTest(Security2Base):
    def test_bolim_admin_cannot_create_plan_for_other_department(self):
        body = {"organization": str(self.org_b.id), "statement": str(self.stmt_b.id), "year": 2026,
                "plan_items": [{"column": str(self.c_val.id), "plan_value": 1}]}
        resp = self._as(self.bolim_a).post(f"{BASE}/plan-create/", body, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("bo'limingizga", resp.content.decode())


class PlantSvodkaScopeTest(Security2Base):
    def setUp(self):
        for org in (self.org_a, self.org_b):
            r = Report.objects.create(organization=org, statement=self.stmt_a, deadline=self.deadline_a,
                                      is_plant_based=True, status="accepted", region=org.region)
            item = ReportItem.objects.create(report=r, statement_column=self.c_val)
            ReportItemInner.objects.create(report_item=item, value="5")

    def test_org_user_does_not_see_other_organizations(self):
        resp = self._as(self.hodim_a).get(f"{BASE}/plant-svodka/", {"statement": str(self.stmt_a.id),
                                                                     "deadline": str(self.deadline_a.id)})
        self.assertEqual(resp.status_code, 200, resp.content)
        text = resp.content.decode()
        self.assertNotIn("Tashkilot B", text)

    def test_rahbariyat_sees_all(self):
        resp = self._as(self.rahbariyat).get(f"{BASE}/plant-svodka/", {"statement": str(self.stmt_a.id),
                                                                       "deadline": str(self.deadline_a.id)})
        self.assertEqual(resp.status_code, 200)

    def test_service_scopes_org_reports_by_user(self):
        from apps.reports.services.plant_svodka import _collect_org_general_reports
        orgs = lambda user: {r.organization_id for r in _collect_org_general_reports(self.stmt_a, self.deadline_a, user)}
        self.assertEqual(orgs(self.hodim_a), {self.org_a.id})
        self.assertEqual(orgs(self.rahbariyat), {self.org_a.id, self.org_b.id})
        self.assertEqual(orgs(None), {self.org_a.id, self.org_b.id})


class MiscScopeTest(Security2Base):
    def test_report_items_require_report_filter(self):
        r = Report.objects.create(organization=self.org_a, statement=self.stmt_a, deadline=self.deadline_a)
        ReportItem.objects.create(report=r, statement_column=self.c_val)
        self.assertEqual(self._as(self.rahbariyat).get(f"{BASE}/report-items/").json(), [])
        self.assertEqual(len(self.client.get(f"{BASE}/report-items/", {"report__id": str(r.id)}).json()), 1)

    def test_deadlines_hidden_from_user_without_organization_or_department(self):
        lonely = self._user("lonely", "tashkilot_hodimi")
        resp = self._as(lonely).get(f"{BASE}/deadlines/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("count", len(data) if isinstance(data, list) else 0), 0)
        resp = self._as(self.rahbariyat).get(f"{BASE}/deadlines/")
        data = resp.json()
        self.assertGreaterEqual(data.get("count", len(data) if isinstance(data, list) else 0), 1)

    def test_import_parse_for_other_organization_is_forbidden(self):
        f = SimpleUploadedFile("r.xlsx", b"PK\x03\x04dummy", "application/octet-stream")
        resp = self._as(self.hodim_a).post(f"{BASE}/import-parse/", {
            "file": f, "statement_id": str(self.stmt_a.id), "organization_id": str(self.org_b.id), "year": 2026,
        }, format="multipart")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_invalid_organization_uuid_is_not_500(self):
        resp = self._as(self.rahbariyat).get(f"{BASE}/individual/", {"organization": "abc"})
        self.assertEqual(resp.status_code, 200)

    def test_login_stats_rejects_garbage_params(self):
        self.assertEqual(self.client.get("/api/v1/statistics/login-stats/", {"monthly": "x" * 30}).status_code, 400)
        self.assertEqual(self.client.get("/api/v1/statistics/login-stats/", {"yearly": "20a6"}).status_code, 400)


class ExcelZipBombTest(Security2Base):
    def test_check_xlsx_zip_rejects_bomb(self):
        with self.assertRaises(UnsafeExcelFile):
            check_xlsx_zip(io.BytesIO(zip_bomb(70 * 1024 * 1024)))
        with self.assertRaises(UnsafeExcelFile):
            check_xlsx_zip(io.BytesIO(zip_bomb(40 * 1024 * 1024)))  # 40 MB / ~40 KB -> nisbat > 200

    def test_check_xlsx_zip_accepts_normal_file_and_rewinds(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("xl/worksheets/sheet1.xml", "<sheet>" + "x" * 5000 + "</sheet>")
        buf.seek(0)
        check_xlsx_zip(buf)
        self.assertEqual(buf.tell(), 0)

    def test_plan_import_rejects_zip_bomb_with_400(self):
        bomb = SimpleUploadedFile("plan.xlsx", zip_bomb(40 * 1024 * 1024),
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertLess(bomb.size, 5 * 1024 * 1024)
        resp = self._as(self.bolim_a).post(
            f"{BASE}/plan-excel/import/?organization={self.org_a.id}&statement={self.stmt_a.id}&year=2026",
            {"file": bomb}, format="multipart")
        self.assertEqual(resp.status_code, 400, resp.content)
