"""Modul administratori API (TZ §17.1–17.2, §19.2, §24.1; plans §11.1-9): ruxsat, a'zolik, ma'lumotnomalar, importlar, sozlamalar, audit."""
import io
from datetime import date

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook
from rest_framework.test import APITestCase

from apps.logs.models import HistoryActionJournal
from apps.yashil.models import (
    CalendarDay, CatalogItem, Mahalla, MahallaUnionRoute, ServiceCapacity, StockMovement, SupplierAssignment,
    SupplierProfile, UnionUnit, YashilMembership, YashilSetting,
)
from apps.yashil.tests._common import (
    BASE, assign_forest, auth, make_district, make_dm, make_forest, make_item, make_mahalla, make_org, make_region,
    make_union, make_user, member, route_union,
)

T = YashilMembership.MemberType
ADMIN = f"{BASE}/admin"


def xlsx_file(header, rows, name="f.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class AdminBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.region = make_region()
        self.district = make_district(self.region)
        self.mahalla = make_mahalla(self.district, source_code="MH-001")
        self.forest = make_forest("Намуна ўрмон хўжалиги")
        self.dm, self.dm_profile = make_dm("Яшил боғлар ДМ")
        assign_forest(self.mahalla, self.forest)
        self.unit = make_union(self.district)
        route_union(self.mahalla, self.unit)
        self.admin = make_user("adm", role="super_admin")
        self.m_user = make_user("m", role="ym_mahalla")
        self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla)
        self.o_user = make_user("o", role="ym_observer")
        self.o_cab = member(self.o_user, T.OBSERVER, can_prepare=False, can_sign=False)
        self.new_user = make_user("valiyev", role="ym_union")

    def as_admin(self):
        self.client.credentials()
        return auth(self.client, self.admin)

    def as_(self, user, cab=None):
        self.client.credentials()
        return auth(self.client, user, cab)


class AdminAccessTest(AdminBase):
    def test_non_admins_get_403(self):
        for user, cab in ((self.m_user, self.m_cab), (self.o_user, self.o_cab)):
            self.as_(user, cab)
            for path in ("memberships/", "calendar/", "settings/", "audit/", "users/search/?q=a", "catalog/"):
                res = self.client.get(f"{ADMIN}/{path}")
                self.assertEqual(res.status_code, 403, path)
                self.assertEqual(res.data["error_code"], "not_module_admin")

    def test_me_reports_admin(self):
        self.as_admin()
        self.assertTrue(self.client.get(f"{BASE}/me/").data["is_admin"])


class MembershipAdminTest(AdminBase):
    def test_user_search(self):
        self.as_admin()
        res = self.client.get(f"{ADMIN}/users/search/", {"q": "valiyev"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual([u["email"] for u in res.data["results"]], [self.new_user.email])
        self.assertEqual(res.data["results"][0]["memberships"], 0)
        self.assertEqual(self.client.get(f"{ADMIN}/users/search/", {"q": "a"}).status_code, 400)  # kamida 2 belgi

    def test_create_membership_then_user_sees_cabinet_and_audit_logged(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/memberships/", {
            "user": str(self.new_user.pk), "member_type": "union", "union_unit": str(self.unit.pk),
            "can_prepare": True, "can_sign": False, "position_title": "Мутахассис", "valid_from": "2026-01-01",
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["cabinet_name"], self.unit.name)
        self.as_(self.new_user)
        me = self.client.get(f"{BASE}/me/").data
        self.assertEqual([c["member_type"] for c in me["cabinets"]], ["union"])
        log = HistoryActionJournal.objects.filter(model_name="YashilMembership", action="add").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user_id, self.admin.pk)

    def test_validation_errors_are_422_with_field(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/memberships/", {"user": str(self.new_user.pk), "member_type": "union"}, format="json")
        self.assertEqual(res.status_code, 422, res.data)
        self.assertEqual(res.data["field"], "union_unit")
        res = self.client.post(f"{ADMIN}/memberships/", {"user": str(self.new_user.pk), "member_type": "observer", "can_sign": True}, format="json")
        self.assertEqual(res.status_code, 422)

    def test_patch_deactivate_and_list_filters(self):
        self.as_admin()
        res = self.client.patch(f"{ADMIN}/memberships/{self.m_cab.pk}/", {"can_sign": False, "valid_to": "2026-12-31"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.m_cab.refresh_from_db()
        self.assertFalse(self.m_cab.can_sign)
        self.assertEqual(self.m_cab.valid_to, date(2026, 12, 31))
        res = self.client.patch(f"{ADMIN}/memberships/{self.m_cab.pk}/", {"member_type": "union"}, format="json")
        self.m_cab.refresh_from_db()
        self.assertEqual(self.m_cab.member_type, "mahalla")  # tur o'zgarmaydi (yangi a'zolik yaratiladi)
        listed = self.client.get(f"{ADMIN}/memberships/", {"member_type": "observer"}).data
        self.assertEqual([r["id"] for r in listed["results"]], [str(self.o_cab.pk)])
        listed = self.client.get(f"{ADMIN}/memberships/", {"q": "m@"}).data
        self.assertIn(str(self.m_cab.pk), [r["id"] for r in listed["results"]])


class ReferenceAdminTest(AdminBase):
    def test_calendar_crud_and_import_dry_run_then_apply(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/calendar/", {"date": "2027-01-01", "kind": "holiday", "note": "Янги йил", "source_ref": "ВМ №1"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self.client.get(f"{ADMIN}/calendar/", {"year": 2027}).data["results"][0]["date"], "2027-01-01")
        f = xlsx_file(["сана", "тури", "изоҳ"], [["08.03.2027", "байрам", "8 март"], ["бузуқ", "байрам", ""]])
        res = self.client.post(f"{ADMIN}/calendar/import/", {"file": f, "dry_run": "1", "source_ref": "ВМ №2"}, format="multipart")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data["created"], res.data["error_count"], res.data["applied"]), (1, 1, False))
        self.assertEqual(res.data["errors"][0]["row"], 3)
        # xato bor — tasdiq ham yozmaydi (hammasi yoki hech narsa)
        f = xlsx_file(["сана", "тури", "изоҳ"], [["08.03.2027", "байрам", "8 март"], ["бузуқ", "байрам", ""]])
        res = self.client.post(f"{ADMIN}/calendar/import/", {"file": f, "dry_run": "0"}, format="multipart")
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.data["error_code"], "import_has_errors")
        self.assertFalse(CalendarDay.objects.filter(date=date(2027, 3, 8)).exists())
        f = xlsx_file(["сана", "тури", "изоҳ"], [["08.03.2027", "байрам", "8 март"]])
        res = self.client.post(f"{ADMIN}/calendar/import/", {"file": f, "dry_run": "0", "source_ref": "ВМ №2"}, format="multipart")
        self.assertEqual((res.status_code, res.data["applied"]), (200, True))
        self.assertEqual(CalendarDay.objects.get(date=date(2027, 3, 8)).source_ref, "ВМ №2")
        day = CalendarDay.objects.get(date=date(2027, 1, 1))
        self.assertEqual(self.client.delete(f"{ADMIN}/calendar/{day.pk}/").status_code, 204)

    def test_bad_file_is_400(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/mahallas/import/", {"file": SimpleUploadedFile("x.xlsx", b"not a zip"), "dry_run": "1"}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["field"], "file")
        f = xlsx_file(["нимадир"], [["1"]])
        res = self.client.post(f"{ADMIN}/mahallas/import/", {"file": f, "dry_run": "1"}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertIn("manba kodi", res.data["message"])

    def test_mahallas_list_create_patch_and_import(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/mahallas/", {"source_code": "MH-002", "name": "Навбаҳор", "district": str(self.district.pk)}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["region"]["id"], str(self.region.pk))  # viloyat tumandan olinadi
        mid = res.data["id"]
        res = self.client.patch(f"{ADMIN}/mahallas/{mid}/", {"is_active": False}, format="json")
        self.assertFalse(res.data["is_active"])
        self.assertEqual(self.client.get(f"{ADMIN}/mahallas/", {"q": "Навба"}).data["count"], 1)
        f = xlsx_file(["манба коди", "вилоят коди", "туман коди", "маҳалла номи"], [["MH-003", self.region.code, self.district.code, "Гулзор"]])
        res = self.client.post(f"{ADMIN}/mahallas/import/", {"file": f, "dry_run": "0"}, format="multipart")
        self.assertEqual((res.data["created"], res.data["applied"]), (1, True))
        self.assertTrue(Mahalla.objects.filter(source_code="MH-003").exists())

    def test_union_units_suppliers_assignments_routes(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/union-units/", {"name": "Янги уюшма", "level": "district", "district": str(self.district.pk)}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        unit2 = res.data["id"]
        org = make_org("Бўстон ўрмон хўжалиги")
        res = self.client.get(f"{ADMIN}/organizations/search/", {"q": "Бўстон"})
        self.assertEqual([o["id"] for o in res.data["results"]], [str(org.pk)])
        self.assertFalse(res.data["results"][0]["is_supplier"])
        res = self.client.post(f"{ADMIN}/suppliers/", {"organization": str(org.pk), "supplier_type": "forest"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(SupplierProfile.objects.filter(organization=org).exists())
        res = self.client.patch(f"{ADMIN}/suppliers/{res.data['id']}/", {"service_regions": [str(self.region.pk)]}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        # biriktirish: eski davrni yopib yangisini ochish
        old = SupplierAssignment.objects.get(mahalla=self.mahalla)
        res = self.client.patch(f"{ADMIN}/assignments/{old.pk}/", {"valid_to": "2026-06-30"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        res = self.client.post(f"{ADMIN}/assignments/", {"mahalla": str(self.mahalla.pk), "organization": str(org.pk),
                                                         "valid_from": "2026-07-01", "source_doc": "Буйруқ №7"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        # kesishuvchi davr — 422
        res = self.client.post(f"{ADMIN}/assignments/", {"mahalla": str(self.mahalla.pk), "organization": str(self.forest.pk),
                                                         "valid_from": "2026-08-01"}, format="json")
        self.assertEqual(res.status_code, 422)
        self.assertEqual(len(self.client.get(f"{ADMIN}/assignments/", {"mahalla": str(self.mahalla.pk)}).data["results"]), 2)
        # marshrut importi
        f = xlsx_file(["маҳалла коди", "уюшма бўлинмаси", "амал бошланиши"], [["MH-001", "Янги уюшма", "01.07.2027"]])
        old_route = MahallaUnionRoute.objects.get(mahalla=self.mahalla)
        self.client.patch(f"{ADMIN}/routes/{old_route.pk}/", {"valid_to": "2027-06-30"}, format="json")
        res = self.client.post(f"{ADMIN}/routes/import/", {"file": f, "dry_run": "0"}, format="multipart")
        self.assertEqual((res.status_code, res.data["created"]), (200, 1), res.data)
        self.assertTrue(MahallaUnionRoute.objects.filter(union_unit_id=unit2).exists())

    def test_catalog_create_and_patch_keeps_code(self):
        self.as_admin()
        res = self.client.post(f"{ADMIN}/catalog/", {"code": "OAK", "name_cyr": "Эман кўчати", "name_lat": "Eman ko'chati",
                                                     "supplier_type": "forest", "item_type": "goods", "category": "seedling", "unit": "tup"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        item = res.data["id"]
        res = self.client.patch(f"{ADMIN}/catalog/{item}/", {"code": "X", "name_cyr": "Эман", "is_active": False}, format="json")
        self.assertEqual((res.data["code"], res.data["name_cyr"], res.data["is_active"]), ("OAK", "Эман", False))
        res = self.client.post(f"{ADMIN}/catalog/", {"code": "BAD", "name_cyr": "x", "name_lat": "x", "supplier_type": "forest",
                                                     "item_type": "goods", "category": "fertilizer", "unit": "kg"}, format="json")
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.data["field"], "category")
        self.assertIn("OAK", [i["code"] for i in self.client.get(f"{ADMIN}/catalog/").data["results"]])


class CapacityAdminTest(AdminBase):
    def setUp(self):
        super().setUp()
        self.svc = make_item("PROT", "Ҳимоя хизмати", "dm", "protection_service", "ga", item_type="service")
        self.dm_user = make_user("dmu", role="ym_dm")
        self.dm_cab = member(self.dm_user, T.SUPPLIER, organization=self.dm)
        self.dm_prep = member(make_user("dmp", role="ym_dm"), T.SUPPLIER, organization=self.dm, can_sign=False)

    def test_admin_sets_capacity(self):
        self.as_admin()
        res = self.client.put(f"{ADMIN}/capacity/", {"organization": str(self.dm.pk), "period": "2027-04",
                                                     "rows": [{"catalog_item": str(self.svc.pk), "capacity": "120"}]}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(ServiceCapacity.objects.get(organization=self.dm, period="2027-04").capacity, 120)
        self.assertEqual(res.data["rows"][0]["capacity"], "120")

    def test_dm_signer_sets_own_capacity_preparer_cannot(self):
        self.as_(self.dm_user, self.dm_cab)
        res = self.client.put(f"{BASE}/stock/capacity/", {"period": "2027-04", "rows": [{"catalog_item": str(self.svc.pk), "capacity": "50"}]}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(ServiceCapacity.objects.get(organization=self.dm).capacity, 50)
        self.as_(self.dm_prep.user, self.dm_prep)
        res = self.client.put(f"{BASE}/stock/capacity/", {"period": "2027-04", "rows": [{"catalog_item": str(self.svc.pk), "capacity": "60"}]}, format="json")
        self.assertEqual(res.status_code, 403)
        res = self.client.put(f"{BASE}/stock/capacity/", {"period": "2027-4", "rows": []}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_capacity_rejects_negative_and_goods(self):
        goods = make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        self.as_admin()
        res = self.client.put(f"{ADMIN}/capacity/", {"organization": str(self.dm.pk), "period": "2027-04",
                                                     "rows": [{"catalog_item": str(goods.pk), "capacity": "5"}]}, format="json")
        self.assertEqual(res.status_code, 422)
        res = self.client.put(f"{ADMIN}/capacity/", {"organization": str(self.dm.pk), "period": "2027-04",
                                                     "rows": [{"catalog_item": str(self.svc.pk), "capacity": "-1"}]}, format="json")
        self.assertEqual(res.status_code, 422)


class SettingsAuditAdminTest(AdminBase):
    def test_settings_get_and_put_new_version(self):
        self.as_admin()
        res = self.client.get(f"{ADMIN}/settings/")
        self.assertEqual(res.status_code, 200)
        keys = {r["key"]: r for r in res.data["results"]}
        self.assertEqual(keys["delivery_workdays"]["value"], 10)
        res = self.client.put(f"{ADMIN}/settings/", {"key": "delivery_workdays", "value": 12, "effective_from": "2099-01-01", "note": "Қарор"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data["results"] if r["key"] == "delivery_workdays")
        self.assertEqual(row["value"], 10)
        self.assertEqual(row["pending"][0]["value"], 12)
        self.assertEqual(YashilSetting.objects.get().changed_by_id, self.admin.pk)
        res = self.client.put(f"{ADMIN}/settings/", {"key": "delivery_workdays", "value": 0}, format="json")
        self.assertEqual((res.status_code, res.data["field"]), (422, "value"))
        res = self.client.put(f"{ADMIN}/settings/", {"key": "delivery_workdays", "value": 9, "effective_from": "2001-01-01"}, format="json")
        self.assertEqual((res.status_code, res.data["field"]), (422, "effective_from"))

    def test_audit_lists_module_changes_only(self):
        self.as_admin()
        self.client.post(f"{ADMIN}/calendar/", {"date": "2027-01-01", "kind": "holiday"}, format="json")
        self.client.put(f"{ADMIN}/settings/", {"key": "review_workdays", "value": 4, "effective_from": "2099-01-01"}, format="json")
        HistoryActionJournal.objects.create(user=self.admin, action="change", model_name="Report", object_id="x")
        res = self.client.get(f"{ADMIN}/audit/")
        self.assertEqual(res.status_code, 200)
        models_seen = {r["model_name"] for r in res.data["results"]}
        self.assertEqual(models_seen, {"CalendarDay", "YashilSetting"})
        self.assertEqual(res.data["results"][0]["user"], self.admin.email)
        res = self.client.get(f"{ADMIN}/audit/", {"model": "CalendarDay"})
        self.assertEqual([r["model_name"] for r in res.data["results"]], ["CalendarDay"])


class OpeningImportTest(AdminBase):
    def setUp(self):
        super().setUp()
        self.ash = make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup")
        self.mul = make_item("MUL", "Мульча", "forest", "mulch", "kg")
        self.s_user = make_user("s", role="tashkilot_rahbari", organization=self.forest)
        self.s_cab = member(self.s_user, T.SUPPLIER, organization=self.forest)
        self.header = ["каталог коди", "миқдор", "ҳужжат рақами", "ҳужжат санаси", "изоҳ"]

    def post(self, rows, dry_run):
        self.as_(self.s_user, self.s_cab)
        return self.client.post(f"{BASE}/stock/opening/import/", {"file": xlsx_file(self.header, rows), "dry_run": dry_run}, format="multipart")

    def test_dry_run_then_apply(self):
        rows = [["ASH", 500, "Д-1", "01.03.2027", ""], ["MUL", "120,5", "Д-1", "01.03.2027", "склад"]]
        res = self.post(rows, "1")
        self.assertEqual((res.status_code, res.data["created"], res.data["applied"]), (200, 2, False), res.data)
        self.assertEqual(StockMovement.objects.count(), 0)
        res = self.post(rows, "0")
        self.assertEqual((res.status_code, res.data["applied"]), (200, True), res.data)
        self.assertEqual(StockMovement.objects.filter(kind="opening").count(), 2)
        # takror — har pozitsiya bir marta
        res = self.post([["ASH", 10, "Д-2", "02.03.2027", ""]], "1")
        self.assertEqual(res.data["error_count"], 1)

    def test_row_errors(self):
        res = self.post([["ASH", 5, "Д-1", "01.03.2027", ""], ["ASH", 6, "Д-1", "01.03.2027", ""],
                         ["BIO", 1, "Д-1", "01.03.2027", ""], ["ZZZ", 1, "Д-1", "01.03.2027", ""], ["MUL", "x", "Д-1", "01.03.2027", ""]], "1")
        self.assertEqual([e["row"] for e in res.data["errors"]], [3, 4, 5, 6])

    def test_only_supplier_cabinet(self):
        self.as_(self.m_user, self.m_cab)
        res = self.client.post(f"{BASE}/stock/opening/import/", {"file": xlsx_file(self.header, []), "dry_run": "1"}, format="multipart")
        self.assertEqual(res.status_code, 403)
