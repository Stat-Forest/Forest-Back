"""Ma'muriyat ekranlari bo'yicha pilot fikrlari: xo'jaliklarni statdan olish, avtomatik kodlar, asos sanasi,
import shablonlari, buyurtmada aloqa telefoni."""
import io
from datetime import date

from django.core.management import call_command
from openpyxl import load_workbook

from apps.yashil.models import CatalogItem, Mahalla, Order, SupplierAssignment, SupplierProfile
from apps.yashil.services import imports
from apps.yashil.tests._common import BASE, make_district, make_item, make_org
from apps.yashil.tests.test_admin_api import ADMIN, AdminBase, xlsx_file
from apps.yashil.tests.test_order_api import OrderApiBase


class SyncForestsTest(AdminBase):
    def setUp(self):
        super().setUp()
        self.a = make_org("Andijon davlat o'rmon xo'jaligi", stir=200240306)
        self.b = make_org("Jondor ko‘chatchilikka ixtisoslashtirilgan davlat o‘rmon xo‘jaligi", region="buxoro")
        self.c = make_org("Наманган давлат ўрмон хўжалиги", region="namangan")
        self.hq = make_org("O'rmon xo'jaligi qo'mitasi", region="republic")
        self.school = make_org("Andijon 5-maktab")

    def test_candidates_are_regional_forest_orgs_without_profile(self):
        self.as_admin()
        res = self.client.get(f"{ADMIN}/suppliers/forest-candidates/")
        self.assertEqual(res.status_code, 200, res.data)
        ids = {r["id"] for r in res.data["results"]}
        self.assertEqual(ids, {str(self.a.id), str(self.b.id), str(self.c.id)})

    def test_sync_creates_forest_profiles_idempotently(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/suppliers/sync-forests/", {}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["created"], 3)
        profile = SupplierProfile.objects.get(organization=self.a)
        self.assertEqual((profile.supplier_type, profile.stir), ("forest", "200240306"))
        self.assertFalse(SupplierProfile.objects.filter(organization__in=[self.hq, self.school]).exists())
        self.assertEqual(self.client.post(f"{ADMIN}/suppliers/sync-forests/", {}, format="json").data["created"], 0)
        # buyurtma formasida asosiy xo'jalikdan boshqalari tanlov sifatida chiqadi
        alternatives = self.as_(self.m_user, self.m_cab).get(f"{BASE}/suppliers/for-mahalla/{self.mahalla.id}/").data["forest"]["alternatives"]
        self.assertEqual(len(alternatives), 3)

    def test_sync_only_selected(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/suppliers/sync-forests/", {"organizations": [str(self.b.id)]}, format="json")
        self.assertEqual(res.data["created"], 1)
        self.assertEqual(set(SupplierProfile.objects.filter(supplier_type="forest").values_list("organization_id", flat=True)),
                         {self.forest.id, self.b.id})

    def test_command_dry_run_then_apply(self):
        out = io.StringIO()
        call_command("yashil_sync_forests", "--dry-run", stdout=out)
        self.assertIn("Andijon davlat o'rmon xo'jaligi", out.getvalue())
        self.assertFalse(SupplierProfile.objects.filter(organization=self.a).exists())
        call_command("yashil_sync_forests", stdout=io.StringIO())
        self.assertTrue(SupplierProfile.objects.filter(organization=self.a).exists())

    def test_non_admin_forbidden(self):
        self.as_(self.m_user, self.m_cab)
        self.assertEqual(self.client.post(f"{ADMIN}/suppliers/sync-forests/", {}, format="json").status_code, 403)


class AutoCodesTest(AdminBase):
    def test_mahalla_code_generated_from_district(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/mahallas/", {"name": "Янги маҳалла", "district": self.district.id}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["source_code"], f"{self.district.code}-001")
        res = self.client.post(f"{ADMIN}/mahallas/", {"name": "Яна бир", "district": self.district.id, "source_code": ""}, format="json")
        self.assertEqual(res.data["source_code"], f"{self.district.code}-002")
        res = self.client.patch(f"{ADMIN}/mahallas/{res.data['id']}/", {"name": "Яна бир маҳалла"}, format="json")
        self.assertEqual(res.data["source_code"], f"{self.district.code}-002")

    def test_catalog_code_generated_by_supplier_type(self):
        self.as_admin()
        make_item("OX-001", "Терак кўчати", "forest", "seedling", "tup")
        body = {"name_cyr": "Эман кўчати", "name_lat": "Eman ko'chati", "supplier_type": "forest", "item_type": "goods",
                "category": "seedling", "unit": "tup"}
        res = self.client.post(f"{ADMIN}/catalog/", body, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["code"], "OX-002")
        res = self.client.post(f"{ADMIN}/catalog/", {**body, "supplier_type": "dm", "category": "fertilizer", "unit": "kg",
                                                     "name_cyr": "Гўнг", "name_lat": "Go'ng"}, format="json")
        self.assertEqual(res.data["code"], "DM-001")

    def test_import_without_code_matches_by_district_and_name(self):
        self.as_admin()
        header = ["Вилоят коди", "Туман коди", "Маҳалла номи"]
        rows = [[self.region.code, self.district.code, "Боғистон маҳалласи"], [self.region.code, self.district.code, "Гулистон"]]
        res = self.client.post(f"{ADMIN}/mahallas/import/", {"file": xlsx_file(header, rows), "dry_run": "0"}, format="multipart")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data["created"], res.data["unchanged"]), (1, 1))
        self.assertEqual(Mahalla.objects.get(name="Гулистон").source_code, f"{self.district.code}-001")


class SourceDocDateTest(AdminBase):
    def test_assignment_keeps_doc_number_and_date_apart(self):
        self.as_admin()
        other = make_district(self.region, code="1703209", name="Бўз тумани")
        m = Mahalla.objects.create(name="Бўз маҳалла", region=self.region, district=other, source_code="BZ-1")
        res = self.client.post(f"{ADMIN}/assignments/", {"mahalla": str(m.id), "organization": str(self.forest.id),
                                                         "valid_from": "2026-11-01", "source_doc": "12-сон буйруқ",
                                                         "source_doc_date": "2026-10-28"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual((res.data["source_doc"], res.data["source_doc_date"]), ("12-сон буйруқ", "2026-10-28"))
        self.assertEqual(SupplierAssignment.objects.get(pk=res.data["id"]).source_doc_date, date(2026, 10, 28))
        res = self.client.post(f"{ADMIN}/routes/", {"mahalla": str(m.id), "union_unit": str(self.unit.id), "valid_from": "2026-11-01",
                                                    "source_doc": "7-сон", "source_doc_date": "2026-10-29"}, format="json")
        self.assertEqual((res.status_code, res.data["source_doc_date"]), (201, "2026-10-29"))

    def test_import_takes_doc_date(self):
        self.as_admin()
        m = Mahalla.objects.create(name="Бўз", region=self.region, district=self.district, source_code="BZ-2")
        f = xlsx_file(["Маҳалла коди", "Хўжалик", "Амал бошланиши"], [["BZ-2", str(self.forest.id), "2026-11-01"]])
        res = self.client.post(f"{ADMIN}/assignments/import/", {"file": f, "dry_run": "0", "source_doc": "3-сон", "source_doc_date": "2026-10-30"}, format="multipart")
        self.assertEqual(res.status_code, 200, res.data)
        a = SupplierAssignment.objects.get(mahalla=m)
        self.assertEqual((a.source_doc, a.source_doc_date), ("3-сон", date(2026, 10, 30)))


class ImportTemplateTest(AdminBase):
    def template(self, url):
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, getattr(res, "data", None))
        self.assertIn("spreadsheetml", res["Content-Type"])
        self.assertIn("attachment", res["Content-Disposition"])
        return b"".join(res.streaming_content) if res.streaming else res.content

    def test_admin_templates_are_accepted_by_their_import(self):
        self.as_admin()
        cases = {
            "mahallas": imports.MAHALLA_HEADERS, "assignments": imports.ASSIGNMENT_HEADERS,
            "routes": imports.ROUTE_HEADERS, "calendar": imports.CALENDAR_HEADERS,
        }
        for kind, headers in cases.items():
            with self.subTest(kind=kind):
                content = self.template(f"{ADMIN}/{kind}/import/")
                sheet = imports.read_sheet(io.BytesIO(content), headers)
                self.assertGreaterEqual(len(sheet.rows), 1)

    def test_sample_mahalla_row_imports_cleanly(self):
        self.as_admin()
        content = self.template(f"{ADMIN}/mahallas/import/")
        result = imports.import_mahallas(io.BytesIO(content), dry_run=True, partial=False)
        self.assertEqual(result.errors, [])

    def test_opening_template_for_supplier(self):
        from apps.yashil.models import YashilMembership
        from apps.yashil.tests._common import make_user, member

        make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup")
        user = make_user("sup", role="tashkilot_rahbari", organization=self.forest)
        cab = member(user, YashilMembership.MemberType.SUPPLIER, organization=self.forest)
        self.as_(user, cab)
        content = self.template(f"{BASE}/stock/opening/import/")
        ws = load_workbook(io.BytesIO(content)).active
        self.assertEqual(ws.cell(2, 1).value, "ASH")
        imports.read_sheet(io.BytesIO(content), imports.OPENING_HEADERS)

    def test_template_needs_admin(self):
        self.as_(self.m_user, self.m_cab)
        self.assertEqual(self.client.get(f"{ADMIN}/mahallas/import/").status_code, 403)


class ContactPhoneTest(OrderApiBase):
    def test_contact_phone_saved_and_in_snapshot(self):
        d = self.create_draft(contact_person="Валиев Анвар", contact_phone="+998 90 123-45-67")
        self.assertEqual(d["contact_phone"], "+998 90 123-45-67")
        _, res = self.sign_and_submit(d["id"], d["version_no"])
        self.assertEqual(res.status_code, 200, res.data)
        version = Order.objects.get(pk=d["id"]).versions.order_by("-version_no").first()
        self.assertEqual(version.snapshot["contact_phone"], "+998 90 123-45-67")

    def test_bad_phone_rejected(self):
        res = self.as_(self.m_user).post(f"{BASE}/orders/", self.draft_payload(contact_phone="телефон йўқ"), format="json")
        self.assertIn(res.status_code, (400, 422))
