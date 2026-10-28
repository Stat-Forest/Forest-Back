"""Buyurtma API: to'liq aylanish, idempotency, versiya, ilovalar, xabarnoma, ochiq QR (TZ §21; Q01–Q10, Q20, Q26)."""
import io
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.yashil.models import Order, OrderState, YashilMembership, YashilNotification
from apps.yashil.services import signing
from apps.yashil.tests._common import (
    BASE, assign_forest, auth, make_district, make_dm, make_forest, make_item, make_mahalla, make_region, make_union,
    make_user, member, route_union,
)
from apps.yashil.tests._eimzo import PINFL, FakeEimzo, fake_sign

T = YashilMembership.MemberType
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class OrderApiBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.other_mahalla = make_mahalla(self.district, "Бошқа маҳалла")
        self.forest = make_forest("Намуна ўрмон хўжалиги")
        self.dm, p = make_dm("Яшил боғлар ДМ"); p.service_regions.add(self.district.region)
        assign_forest(self.mahalla, self.forest)
        self.unit = make_union(self.district); route_union(self.mahalla, self.unit)
        self.ash = make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup")
        self.mul = make_item("MUL", "Мульча", "forest", "mulch", "kg")
        self.bio = make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        self.m_user = make_user("m", role="ym_mahalla", pinfl=PINFL)
        self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla)
        self.u_user = make_user("u", role="ym_union"); self.u_cab = member(self.u_user, T.UNION, union_unit=self.unit, can_sign=False)
        self.s_user = make_user("s", role="tashkilot_rahbari", organization=self.forest, pinfl="55555555555555")
        self.s_cab = member(self.s_user, T.SUPPLIER, organization=self.forest)
        self.o_user = make_user("o", role="ym_observer"); member(self.o_user, T.OBSERVER, can_prepare=False, can_sign=False)
        self.x_user = make_user("x", role="ym_mahalla"); member(self.x_user, T.MAHALLA, mahalla=self.other_mahalla)
        self.eimzo = FakeEimzo()

    def as_(self, user, cabinet=None):
        self.client.credentials()
        return auth(self.client, user, cabinet)

    def draft_payload(self, **over):
        p = {
            "route": "forest", "supplier_org": str(self.forest.pk), "title": "Боғистонга кўчат",
            "address": "Боғистон, марказий кўча", "lat": "41.311081", "lon": "69.240562", "area_ha": "0.5",
            "lines": [{"catalog_item": str(self.ash.pk), "qty": "300"}],
        }
        p.update(over)
        return p

    def create_draft(self, **over):
        res = self.as_(self.m_user).post(f"{BASE}/orders/", self.draft_payload(**over), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data

    def sign_and_submit(self, order_id, version_no, key="k1"):
        with patch.object(signing, "eimzo_api", self.eimzo):
            doc = self.client.post(f"{BASE}/orders/{order_id}/document/", {"version_no": version_no}, format="json")
            self.assertEqual(doc.status_code, 200, doc.data)
            res = self.client.post(
                f"{BASE}/orders/{order_id}/submit/",
                {"document_version_id": doc.data["document_version"]["id"], "nonce": doc.data["nonce"],
                 "pkcs7": fake_sign(doc.data["sign_text"]), "version_no": version_no},
                format="json", HTTP_IDEMPOTENCY_KEY=key,
            )
        return doc.data, res

    def submitted_order(self):
        d = self.create_draft()
        _, res = self.sign_and_submit(d["id"], d["version_no"])
        self.assertEqual(res.status_code, 200, res.data)
        return Order.objects.get(pk=d["id"])


class DraftAndSubmitTest(OrderApiBase):
    def test_create_draft_edit_and_version_conflict(self):
        d = self.create_draft()
        self.assertEqual((d["state"], d["version_no"], d["number"]), ("draft", 1, None))
        res = self.client.patch(f"{BASE}/orders/{d['id']}/", {"title": "Янги ном", "version_no": 1,
                                "lines": [{"catalog_item": str(self.ash.pk), "qty": "350"}]}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["lines"][0]["qty"], "350")
        res = self.client.patch(f"{BASE}/orders/{d['id']}/", {"title": "X", "version_no": 7}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["error_code"], "version_conflict")

    def test_q03_stock_is_not_checked_and_q02_catalog_is_restricted(self):
        self.create_draft(lines=[{"catalog_item": str(self.ash.pk), "qty": "100000"}])
        res = self.client.post(f"{BASE}/orders/", self.draft_payload(lines=[{"catalog_item": str(self.bio.pk), "qty": "10"}]), format="json")
        self.assertEqual(res.status_code, 422)
        self.assertEqual((res.data["error_code"], res.data["field"]), ("line_supplier_mismatch", "lines"))

    def test_norm_violation_reported_with_field(self):
        d = self.create_draft(lines=[{"catalog_item": str(self.mul.pk), "qty": "500"}], base_seedlings=100)
        from datetime import date
        from apps.yashil.models import NormRule
        NormRule.objects.create(code="mulch_per_tup_kg", description="4 кг/туп", applies_to_category="mulch", params={"max_per_tup": 4}, effective_from=date(2026, 1, 1))
        res = self.client.post(f"{BASE}/orders/{d['id']}/document/", {"version_no": 1}, format="json")
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.data["error_code"], "norm_violation")

    def test_q04_point_lands_in_document_and_q06_submit_signs(self):
        d = self.create_draft()
        doc, res = self.sign_and_submit(d["id"], 1)
        self.assertEqual(doc["document_version"]["content"]["point"], "41.311081, 69.240562")
        self.assertEqual(doc["mode"], "challenge")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["state"], "union_new")
        self.assertEqual(res.data["number"], f"YM-{__import__('datetime').date.today().year}-000001")
        self.assertEqual(res.data["documents"][0]["current_version"]["status"], "signed")
        self.assertEqual(res.data["documents"][0]["current_version"]["signatures"][0]["role"], "mahalla")
        self.assertIn("review_due", res.data["deadline"])
        self.assertEqual(YashilNotification.objects.filter(recipient_user=self.u_user, kind="order_new_union").count(), 1)

    def test_q05_bad_signature_keeps_draft(self):
        d = self.create_draft()
        with patch.object(signing, "eimzo_api", self.eimzo):
            doc = self.client.post(f"{BASE}/orders/{d['id']}/document/", {"version_no": 1}, format="json").data
            res = self.client.post(f"{BASE}/orders/{d['id']}/submit/", {
                "document_version_id": doc["document_version"]["id"], "nonce": doc["nonce"],
                "pkcs7": fake_sign("noto'g'ri matn"), "version_no": 1}, format="json", HTTP_IDEMPOTENCY_KEY="bad")
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.data["error_code"], "signature_invalid")
        self.assertEqual(Order.objects.get(pk=d["id"]).state, OrderState.DRAFT)

    def test_submit_requires_idempotency_key_and_replays_same_response(self):
        d = self.create_draft()
        with patch.object(signing, "eimzo_api", self.eimzo):
            doc = self.client.post(f"{BASE}/orders/{d['id']}/document/", {"version_no": 1}, format="json").data
            body = {"document_version_id": doc["document_version"]["id"], "nonce": doc["nonce"],
                    "pkcs7": fake_sign(doc["sign_text"]), "version_no": 1}
            res = self.client.post(f"{BASE}/orders/{d['id']}/submit/", body, format="json")
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.data["error_code"], "idempotency_key_required")
            r1 = self.client.post(f"{BASE}/orders/{d['id']}/submit/", body, format="json", HTTP_IDEMPOTENCY_KEY="same")
            r2 = self.client.post(f"{BASE}/orders/{d['id']}/submit/", body, format="json", HTTP_IDEMPOTENCY_KEY="same")
            r3 = self.client.post(f"{BASE}/orders/{d['id']}/submit/", {**body, "version_no": 2}, format="json", HTTP_IDEMPOTENCY_KEY="same")
        self.assertEqual((r1.status_code, r2.status_code), (200, 200))
        self.assertEqual(r1.data["number"], r2.data["number"])
        self.assertEqual(Order.objects.get(pk=d["id"]).versions.count(), 1)
        self.assertEqual(r3.status_code, 409)
        self.assertEqual(r3.data["error_code"], "idempotency_mismatch")


class ReviewFlowTest(OrderApiBase):
    def test_full_flow_union_forward_supplier_accept(self):
        o = self.submitted_order()
        self.as_(self.u_user)
        lst = self.client.get(f"{BASE}/orders/?state=union_new").data
        self.assertEqual([r["number"] for r in lst["results"]], [o.number])
        self.assertEqual(self.client.get(f"{BASE}/orders/{o.pk}/").data["actions"], ["review"])
        self.assertEqual(self.client.post(f"{BASE}/orders/{o.pk}/review/", {}, format="json", HTTP_IDEMPOTENCY_KEY="r1").status_code, 200)
        res = self.client.post(f"{BASE}/orders/{o.pk}/forward/", {"version_no": 1}, format="json", HTTP_IDEMPOTENCY_KEY="f1")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["state"], "supplier_new")
        self.as_(self.s_user)
        self.assertEqual(self.client.get(f"{BASE}/orders/").data["count"], 1)
        self.client.post(f"{BASE}/orders/{o.pk}/review/", {}, format="json", HTTP_IDEMPOTENCY_KEY="r2")
        res = self.client.post(f"{BASE}/orders/{o.pk}/accept/", {"executor_name": "Иброҳимов А.", "version_no": 1}, format="json", HTTP_IDEMPOTENCY_KEY="a1")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["state"], "execution")
        self.assertIsNotNone(res.data["delivery_due"])
        self.assertEqual(res.data["deadline"]["stage"], "delivery")
        self.as_(self.m_user)
        detail = self.client.get(f"{BASE}/orders/{o.pk}/").data
        self.assertEqual([e["action"] for e in detail["events"]], ["submit", "review", "forward", "review", "accept"])
        self.assertEqual(detail["actions"], [])

    def test_q07_return_without_comment_and_q08_resubmit(self):
        o = self.submitted_order()
        self.as_(self.u_user)
        self.client.post(f"{BASE}/orders/{o.pk}/review/", {}, format="json", HTTP_IDEMPOTENCY_KEY="r")
        res = self.client.post(f"{BASE}/orders/{o.pk}/return/", {"reason_code": "address", "comment": " ", "version_no": 1}, format="json", HTTP_IDEMPOTENCY_KEY="x1")
        self.assertEqual(res.status_code, 422)
        self.assertEqual((res.data["error_code"], res.data["field"]), ("comment_required", "comment"))
        res = self.client.post(f"{BASE}/orders/{o.pk}/return/", {"reason_code": "address", "comment": "Манзилни аниқлаштиринг", "fields": ["address"], "version_no": 1}, format="json", HTTP_IDEMPOTENCY_KEY="x2")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["state"], "returned")
        self.assertEqual(res.data["last_return"]["comment"], "Манзилни аниқлаштиринг")
        self.as_(self.m_user)
        self.assertTrue(YashilNotification.objects.filter(recipient_user=self.m_user, kind="order_returned").exists())
        self.assertEqual(self.client.get(f"{BASE}/orders/{o.pk}/").data["actions"], ["edit", "submit"])
        self.assertEqual(self.client.patch(f"{BASE}/orders/{o.pk}/", {"address": "Янги манзил", "version_no": 1}, format="json").status_code, 200)
        _, res = self.sign_and_submit(o.pk, 1, key="k2")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data["number"], res.data["version_no"], res.data["state"]), (o.number, 2, "union_new"))
        self.assertEqual(len(res.data["versions"]), 2)
        self.assertEqual(res.data["documents"][0]["current_version"]["version_no"], 2)

    def test_q09_dm_route_goes_to_dm_cabinet_only(self):
        d = self.create_draft(route="dm", supplier_org=str(self.dm.pk), lines=[{"catalog_item": str(self.bio.pk), "qty": "50"}], base_seedlings=20)
        _, res = self.sign_and_submit(d["id"], 1)
        self.assertEqual(res.status_code, 200, res.data)
        self.as_(self.u_user)
        self.client.post(f"{BASE}/orders/{d['id']}/review/", {}, format="json", HTTP_IDEMPOTENCY_KEY="r")
        self.client.post(f"{BASE}/orders/{d['id']}/forward/", {"version_no": 1}, format="json", HTTP_IDEMPOTENCY_KEY="f")
        self.as_(self.s_user)
        self.assertEqual(self.client.get(f"{BASE}/orders/").data["count"], 0)
        self.assertEqual(self.client.get(f"{BASE}/orders/{d['id']}/").status_code, 404)

    def test_q20_other_mahalla_cannot_open_order_or_document(self):
        o = self.submitted_order()
        doc_id = o.documents.get().current_version_id
        self.as_(self.x_user)
        self.assertEqual(self.client.get(f"{BASE}/orders/{o.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"{BASE}/documents/{doc_id}/").status_code, 404)
        self.assertEqual(self.client.get(f"{BASE}/orders/").data["count"], 0)
        self.as_(self.o_user)
        self.assertEqual(self.client.get(f"{BASE}/orders/{o.pk}/").status_code, 200)
        self.assertEqual(self.client.post(f"{BASE}/orders/{o.pk}/review/", {}, format="json", HTTP_IDEMPOTENCY_KEY="z").status_code, 403)

    def test_public_verify_and_html(self):
        o = self.submitted_order()
        v = o.documents.get().current_version
        self.client.credentials()
        res = self.client.get(f"{BASE}/verify/{v.qr_token}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data["status"], res.data["number"]), ("valid", o.number))
        self.assertNotIn("41.311", str(res.data))
        self.assertEqual(self.client.get(f"{BASE}/verify/nope/").status_code, 404)
        self.as_(self.m_user)
        html = self.client.get(f"{BASE}/documents/{v.pk}/html/")
        self.assertEqual(html.status_code, 200)
        self.assertIn("Ҳақиқий", html.content.decode())


class AttachmentsAndNotificationsTest(OrderApiBase):
    def test_upload_limits_and_listing(self):
        d = self.create_draft()
        res = self.client.post(f"{BASE}/orders/{d['id']}/attachments/", {"file": SimpleUploadedFile("joy.png", PNG, "image/png"), "kind": "photo"}, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        res = self.client.post(f"{BASE}/orders/{d['id']}/attachments/", {"file": SimpleUploadedFile("x.html", b"<script>", "text/html")}, format="multipart")
        self.assertEqual(res.status_code, 400)
        detail = self.client.get(f"{BASE}/orders/{d['id']}/").data
        self.assertEqual(len(detail["attachments"]), 1)
        self.assertTrue(detail["attachments"][0]["url"].startswith("/media/documents/yashil/orders/"))
        self.assertIn("?t=", detail["attachments"][0]["url"])
        aid = detail["attachments"][0]["id"]
        self.assertEqual(self.client.delete(f"{BASE}/orders/{d['id']}/attachments/{aid}/").status_code, 204)

    def test_notifications_list_and_read(self):
        self.submitted_order()
        self.as_(self.u_user)
        me = self.client.get(f"{BASE}/me/").data
        self.assertEqual(me["unread_notifications"], 1)
        lst = self.client.get(f"{BASE}/notifications/").data
        self.assertEqual(lst["results"][0]["kind"], "order_new_union")
        nid = lst["results"][0]["id"]
        self.assertEqual(self.client.post(f"{BASE}/notifications/{nid}/read/").status_code, 200)
        self.assertEqual(self.client.get(f"{BASE}/me/").data["unread_notifications"], 0)
        self.assertEqual(self.client.post(f"{BASE}/notifications/read-all/").status_code, 200)
