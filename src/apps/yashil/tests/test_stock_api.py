"""Ombor API: xulosa, harakatlar, kirim (idempotent), teskari operatsiya, quvvat; ko'lam (TZ §9, §14; Q27, Q28, Q30)."""
from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.yashil.models import Order, OrderLine, OrderState, ServiceCapacity, StockMovement, YashilMembership
from apps.yashil.services import ledger
from apps.yashil.tests._common import (
    BASE, assign_forest, auth, make_district, make_dm, make_forest, make_item, make_mahalla, make_region, make_union,
    make_user, member, route_union,
)

T = YashilMembership.MemberType
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class StockApiBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.forest = make_forest()
        self.other_forest = make_forest("Бошқа хўжалик")
        self.dm, p = make_dm(); p.service_regions.add(self.district.region)
        assign_forest(self.mahalla, self.forest)
        self.unit = make_union(self.district); route_union(self.mahalla, self.unit)
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        self.mul = make_item("MUL", "Мульча", "forest", "mulch", "kg")
        self.bio = make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        self.prt = make_item("PRT", "Ҳимоя", "dm", "protection_service", "daraxt", item_type="service")
        self.m_user = make_user("m", role="ym_mahalla"); self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla)
        self.f_user = make_user("f", role="tashkilot_hodimi", organization=self.forest)
        self.f_cab = member(self.f_user, T.SUPPLIER, organization=self.forest, can_sign=False)
        self.fs_user = make_user("fs", role="tashkilot_rahbari", organization=self.forest)
        self.fs_cab = member(self.fs_user, T.SUPPLIER, organization=self.forest)
        self.d_user = make_user("d", role="tashkilot_hodimi", organization=self.dm)
        self.d_cab = member(self.d_user, T.SUPPLIER, organization=self.dm, can_sign=False)
        self.o_user = make_user("o", role="ym_observer"); self.o_cab = member(self.o_user, T.OBSERVER, can_prepare=False, can_sign=False)
        self.fw = ledger.default_warehouse(self.forest)

    def as_(self, user, cabinet=None):
        self.client.credentials()
        return auth(self.client, user, cabinet)

    def receipt(self, payload, key="r1", fmt="json", **extra):
        return self.client.post(f"{BASE}/stock/receipts/", payload, format=fmt, HTTP_IDEMPOTENCY_KEY=key, **extra)


class StockSummaryTest(StockApiBase):
    def test_supplier_sees_own_summary_with_shortage_and_observer_sees_by_organization(self):
        ledger.post_opening(self.fw, self.ash, Decimal("100"), self.f_cab, doc_number="ИНВ-1", doc_date=date(2026, 12, 31))
        order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest, union_unit=self.unit,
                                     created_by_membership=self.m_cab, number="YM-2027-000001", state=OrderState.EXECUTION)
        OrderLine.objects.create(order=order, catalog_item=self.ash, qty=Decimal("300"))
        ledger.allocate_for_acceptance(order, self.f_cab, accepted_on=date(2027, 1, 11), delivery_due=date(2027, 1, 25), executor_name="X")
        res = self.as_(self.f_user, self.f_cab).get(f"{BASE}/stock/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["warehouse"]["name"], "Асосий омбор")
        row = next(r for r in res.data["rows"] if r["code"] == "ASH")
        self.assertEqual((row["balance"], row["shortage"], row["allocated"]), ("-200", "200", "300"))
        self.assertEqual(res.data["shortage_count"], 1)
        # Kuzatuvchi — tashkilot ko'rsatib ko'radi, kirim kirita olmaydi (TZ §9.4)
        res = self.as_(self.o_user, self.o_cab).get(f"{BASE}/stock/", {"organization": str(self.forest.pk)})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["rows"][0]["shortage"], "200")
        res = self.receipt({"catalog_item": str(self.ash.pk), "qty": "10", "doc_number": "К", "doc_date": "2027-01-05"})
        self.assertEqual(res.status_code, 403)
        # Mahalla kabineti omborni ko'rmaydi
        res = self.as_(self.m_user, self.m_cab).get(f"{BASE}/stock/")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["error_code"], "forbidden")

    def test_supplier_cannot_read_other_organization(self):
        res = self.as_(self.f_user, self.f_cab).get(f"{BASE}/stock/", {"organization": str(self.other_forest.pk)})
        self.assertEqual(res.status_code, 403)

    def test_dm_capacity_endpoint(self):
        ServiceCapacity.objects.create(organization=self.dm, catalog_item=self.prt, period="2027-01", capacity=Decimal("100"))
        res = self.as_(self.d_user, self.d_cab).get(f"{BASE}/stock/capacity/", {"period": "2027-01"})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual([(r["code"], r["capacity"], r["used"], r["available"]) for r in res.data["rows"]], [("PRT", "100", "0", "100")])
        res = self.client.get(f"{BASE}/stock/capacity/", {"period": "2027-1"})
        self.assertEqual((res.status_code, res.data["error_code"]), (400, "invalid_format"))


class ReceiptApiTest(StockApiBase):
    def test_q28_receipt_with_file_is_idempotent_and_warns_on_duplicate_doc_number(self):
        self.as_(self.f_user, self.f_cab)
        f = SimpleUploadedFile("kirim.png", PNG, content_type="image/png")
        res = self.receipt({"catalog_item": str(self.ash.pk), "qty": "150", "doc_number": "К-1", "doc_date": "2027-01-05",
                            "note": "Питомникдан", "file": f}, fmt="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual((res.data["movement"]["kind"], res.data["movement"]["qty"], res.data["balance"]), ("receipt", "150", "150"))
        self.assertTrue(res.data["movement"]["file_url"].startswith("/media/documents/yashil/stock/"))
        self.assertIn("?t=", res.data["movement"]["file_url"])
        self.assertEqual(res.data["warnings"], [])
        again = self.receipt({"catalog_item": str(self.ash.pk), "qty": "150", "doc_number": "К-1", "doc_date": "2027-01-05", "note": "Питомникдан",
                              "file": SimpleUploadedFile("kirim.png", PNG, content_type="image/png")}, fmt="multipart")
        self.assertEqual(again.status_code, 201)
        self.assertEqual(StockMovement.objects.filter(kind="receipt").count(), 1)
        dup = self.receipt({"catalog_item": str(self.ash.pk), "qty": "20", "doc_number": "К-1", "doc_date": "2027-01-06"}, key="r2")
        self.assertEqual(dup.status_code, 201, dup.data)
        self.assertEqual(dup.data["warnings"][0]["code"], "doc_number_duplicate")
        self.assertEqual(dup.data["balance"], "170")
        res = self.client.get(f"{BASE}/stock/movements/", {"item": str(self.ash.pk)})
        self.assertEqual(res.status_code, 200)
        self.assertEqual([m["doc_number"] for m in res.data["results"]], ["К-1", "К-1"])

    def test_receipt_validation_errors_follow_contract(self):
        self.as_(self.f_user, self.f_cab)
        res = self.client.post(f"{BASE}/stock/receipts/", {"catalog_item": str(self.ash.pk), "qty": "5"}, format="json")
        self.assertEqual((res.status_code, res.data["error_code"]), (400, "idempotency_key_required"))
        res = self.receipt({"catalog_item": str(self.ash.pk), "qty": "0", "doc_number": "К", "doc_date": "2027-01-05"})
        self.assertEqual((res.status_code, res.data["error_code"], res.data["field"]), (422, "invalid_qty", "qty"))
        res = self.receipt({"catalog_item": str(self.bio.pk), "qty": "5", "doc_number": "К", "doc_date": "2027-01-05"}, key="r3")
        self.assertEqual((res.status_code, res.data["error_code"]), (422, "item_supplier_mismatch"))
        res = self.receipt({"catalog_item": str(self.ash.pk), "qty": "5", "doc_number": "К", "doc_date": "05.01.2027"}, key="r4")
        self.assertEqual((res.status_code, res.data["error_code"]), (400, "validation"))

    def test_opening_once_and_q27_zero_stock_is_fine(self):
        self.as_(self.f_user, self.f_cab)
        res = self.client.post(f"{BASE}/stock/opening/", {"catalog_item": str(self.ash.pk), "qty": "100", "doc_number": "ИНВ", "doc_date": "2026-12-31"},
                               format="json", HTTP_IDEMPOTENCY_KEY="o1")
        self.assertEqual(res.status_code, 201, res.data)
        res = self.client.post(f"{BASE}/stock/opening/", {"catalog_item": str(self.ash.pk), "qty": "5", "doc_number": "ИНВ", "doc_date": "2026-12-31"},
                               format="json", HTTP_IDEMPOTENCY_KEY="o2")
        self.assertEqual((res.status_code, res.data["error_code"]), (409, "opening_exists"))
        res = self.client.get(f"{BASE}/stock/")
        self.assertEqual(next(r for r in res.data["rows"] if r["code"] == "MUL")["balance"], "0")


class ReversalApiTest(StockApiBase):
    def test_reversal_request_and_approval_flow(self):
        mv, _ = ledger.post_receipt(self.fw, self.ash, Decimal("50"), self.f_cab, doc_number="К-9", doc_date=date(2027, 1, 5))
        self.as_(self.f_user, self.f_cab)
        res = self.client.post(f"{BASE}/stock/reversals/", {"movement": str(mv.pk), "note": "Хато"}, format="json", HTTP_IDEMPOTENCY_KEY="v1")
        self.assertEqual(res.status_code, 201, res.data)
        rev_id = res.data["movement"]["id"]
        self.assertEqual(res.data["movement"]["status"], "pending_approval")
        res = self.client.post(f"{BASE}/stock/reversals/{rev_id}/approve/", {}, format="json", HTTP_IDEMPOTENCY_KEY="a1")
        self.assertEqual((res.status_code, res.data["error_code"]), (403, "cannot_sign"))
        res = self.as_(self.fs_user, self.fs_cab).post(f"{BASE}/stock/reversals/{rev_id}/approve/", {"note": "Тасдиқ"}, format="json", HTTP_IDEMPOTENCY_KEY="a2")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data["movement"]["status"], res.data["balance"]), ("posted", "0"))
        res = self.client.get(f"{BASE}/stock/movements/", {"status": "pending_approval"})
        self.assertEqual(res.data["count"], 0)

    def test_reject_requires_note_and_other_org_cannot_touch(self):
        mv, _ = ledger.post_receipt(self.fw, self.ash, Decimal("50"), self.f_cab, doc_number="К-9", doc_date=date(2027, 1, 5))
        rev = ledger.request_reversal(mv, self.f_cab, note="x")
        res = self.as_(self.fs_user, self.fs_cab).post(f"{BASE}/stock/reversals/{rev.pk}/reject/", {}, format="json", HTTP_IDEMPOTENCY_KEY="j1")
        self.assertEqual((res.status_code, res.data["error_code"]), (422, "note_required"))
        res = self.as_(self.d_user, self.d_cab).post(f"{BASE}/stock/reversals/{rev.pk}/reject/", {"note": "x"}, format="json", HTTP_IDEMPOTENCY_KEY="j2")
        self.assertEqual(res.status_code, 404)
        res = self.as_(self.fs_user, self.fs_cab).post(f"{BASE}/stock/reversals/{rev.pk}/reject/", {"note": "Асос йўқ"}, format="json", HTTP_IDEMPOTENCY_KEY="j3")
        self.assertEqual((res.status_code, res.data["movement"]["status"]), (200, "rejected"))


class AcceptStockApiTest(StockApiBase):
    def test_accept_response_carries_stock_result_and_dm_insufficient_lines(self):
        order = Order.objects.create(mahalla=self.mahalla, route="dm", supplier_org=self.dm, union_unit=self.unit,
                                     created_by_membership=self.m_cab, number="YM-2027-000001", state=OrderState.SUPPLIER_REVIEW)
        OrderLine.objects.create(order=order, catalog_item=self.bio, qty=Decimal("50"))
        res = self.as_(self.d_user, self.d_cab).post(f"{BASE}/orders/{order.pk}/accept/", {"executor_name": "И.", "version_no": 1},
                                                      format="json", HTTP_IDEMPOTENCY_KEY="ac1")
        self.assertEqual((res.status_code, res.data["error_code"]), (422, "stock_insufficient"))
        self.assertEqual(res.data["lines"][0]["code"], "BIO")
        order.refresh_from_db(); self.assertEqual(order.state, OrderState.SUPPLIER_REVIEW)
        ledger.post_receipt(ledger.default_warehouse(self.dm), self.bio, Decimal("60"), self.d_cab, doc_number="К", doc_date=date(2027, 1, 5))
        res = self.client.post(f"{BASE}/orders/{order.pk}/accept/", {"executor_name": "И.", "version_no": 1}, format="json", HTTP_IDEMPOTENCY_KEY="ac2")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["state"], "execution")
        self.assertEqual(res.data["acceptance"]["result"]["lines"][0]["balance_after"], "10")
        self.assertFalse(res.data["acceptance"]["result"]["has_shortage"])
