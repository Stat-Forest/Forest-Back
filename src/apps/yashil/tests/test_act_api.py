"""Dalolatnoma API: to'liq aylanish ikki imzo bilan, ilova, qaytarish, reestr ko'lami, QR (TZ §10, §12, §14, §21)."""
from datetime import date, datetime, timezone as tz
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.yashil.models import Act, Order, OrderLine, OrderState, YashilMembership
from apps.yashil.services import signing
from apps.yashil.services import transitions as tr
from apps.yashil.tests._common import (
    BASE, assign_forest, auth, make_district, make_forest, make_item, make_mahalla, make_region, make_union, make_user,
    member, route_union,
)
from apps.yashil.tests._eimzo import FakeEimzo, fake_sign

T = YashilMembership.MemberType
NOW = datetime(2027, 1, 11, 9, tzinfo=tz.utc)
LATER = datetime(2027, 1, 15, 9, tzinfo=tz.utc)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
M_PINFL, S_PINFL = "31234567890123", "55555555555555"


class ActApiBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.other_mahalla = make_mahalla(self.district, "Бошқа маҳалла")
        self.forest = make_forest()
        assign_forest(self.mahalla, self.forest)
        self.unit = make_union(self.district); route_union(self.mahalla, self.unit)
        self.ash = make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup")
        self.mul = make_item("MUL", "Мульча", "forest", "mulch", "kg")
        self.m_user = make_user("m", role="ym_mahalla", pinfl=M_PINFL); self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla)
        self.u_user = make_user("u", role="ym_union"); self.u_cab = member(self.u_user, T.UNION, union_unit=self.unit, can_sign=False)
        self.s_user = make_user("s", role="tashkilot_rahbari", organization=self.forest, pinfl=S_PINFL)
        self.s_cab = member(self.s_user, T.SUPPLIER, organization=self.forest)
        self.o_user = make_user("o", role="ym_observer"); self.o_cab = member(self.o_user, T.OBSERVER, can_prepare=False, can_sign=False)
        self.x_user = make_user("x", role="ym_mahalla"); self.x_cab = member(self.x_user, T.MAHALLA, mahalla=self.other_mahalla)
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest, union_unit=self.unit,
                                          created_by_membership=self.m_cab, title="Кўчат", address="Боғистон", number="YM-2027-000001",
                                          state=OrderState.SUPPLIER_REVIEW, lat=Decimal("41.3"), lon=Decimal("69.2"), area_ha=Decimal("0.5"))
        self.l_ash = OrderLine.objects.create(order=self.order, catalog_item=self.ash, qty=Decimal("100"))
        self.l_mul = OrderLine.objects.create(order=self.order, catalog_item=self.mul, qty=Decimal("50"))
        with patch("django.utils.timezone.now", return_value=NOW):
            tr.accept(self.order, self.s_cab, executor_name="Иброҳимов")
        # Barcha so'rovlar 2027-01-15 da (token faolligi va yetkazish sanasi tekshiruvi bir xil vaqtda)
        patcher = patch("django.utils.timezone.now", return_value=LATER)
        patcher.start()
        self.addCleanup(patcher.stop)

    def as_(self, user, cabinet=None):
        self.client.credentials()
        return auth(self.client, user, cabinet)

    def create_act(self, lines, key="c1", **over):
        payload = {"delivery_date": "2027-01-14", "responsible": "Иброҳимов", "note": "Етказилди",
                   "lines": [{"order_line": str(l), "qty": q} for l, q in lines]}
        payload.update(over)
        return self.as_(self.s_user, self.s_cab).post(f"{BASE}/orders/{self.order.pk}/acts/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key)

    def attach(self, act_id):
        return self.client.post(f"{BASE}/acts/{act_id}/attachments/", {"file": SimpleUploadedFile("foto.png", PNG, content_type="image/png"), "kind": "photo"},
                                format="multipart")

    def sign(self, act_id, user, cabinet, pinfl, key):
        with patch.object(signing, "eimzo_api", FakeEimzo(pinfl=pinfl)):
            self.as_(user, cabinet)
            task = self.client.post(f"{BASE}/acts/{act_id}/sign-task/", {}, format="json")
            if task.status_code != 200:
                return task
            return self.client.post(f"{BASE}/acts/{act_id}/sign/", {"document_version_id": task.data["document_version_id"], "nonce": task.data["nonce"],
                                                                   "pkcs7": fake_sign(task.data["sign_text"])}, format="json", HTTP_IDEMPOTENCY_KEY=key)


class ActFlowApiTest(ActApiBase):
    def test_full_cycle_two_signatures_partial_then_closed(self):
        res = self.create_act([(self.l_ash.pk, "60")])
        self.assertEqual(res.status_code, 201, res.data)
        act_id = res.data["id"]
        self.assertEqual((res.data["number"], res.data["status"], res.data["is_partial"]), ("YM-2027-000001/A1", "draft", True))
        self.assertEqual(res.data["current_version"]["lines"][0]["qty"], "60")
        self.assertEqual(res.data["actions"], ["edit", "attach", "sign", "cancel"])
        # Dalil bo'lmasa imzo topshirig'i 422
        task = self.client.post(f"{BASE}/acts/{act_id}/sign-task/", {}, format="json")
        self.assertEqual((task.status_code, task.data["error_code"]), (422, "evidence_required"))
        self.assertEqual(self.attach(act_id).status_code, 201)
        res = self.sign(act_id, self.s_user, self.s_cab, S_PINFL, "s1")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "mahalla_review")
        self.assertEqual(res.data["document"]["current_version"]["status"], "partly_signed")
        # Mahalla ko'radi va imzolaydi
        res = self.as_(self.m_user, self.m_cab).get(f"{BASE}/acts/", {"status": "mahalla_review"})
        self.assertEqual((res.status_code, res.data["count"]), (200, 1))
        self.assertEqual(res.data["results"][0]["actions"], ["approve", "return"])
        res = self.sign(act_id, self.m_user, self.m_cab, M_PINFL, "m1")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data["status"], res.data["order"]["state"]), ("approved", "partial"))
        res = self.client.get(f"{BASE}/orders/{self.order.pk}/")
        self.assertEqual(res.data["state"], "partial")
        self.assertEqual([(l["accepted_qty"], l["remaining_qty"]) for l in res.data["lines"]], [("60", "40"), ("0", "50")])
        self.assertEqual(len(res.data["acts"]), 1)
        self.assertEqual(res.data["deadline"]["stage"], "delivery")
        # Qolgan hajm bitta akt bilan
        res = self.create_act([(self.l_ash.pk, "40"), (self.l_mul.pk, "50")], key="c2")
        self.assertEqual(res.status_code, 201, res.data)
        a2 = res.data["id"]
        self.assertEqual((res.data["number"], res.data["is_partial"]), ("YM-2027-000001/A2", False))
        self.attach(a2)
        self.sign(a2, self.s_user, self.s_cab, S_PINFL, "s2")
        res = self.sign(a2, self.m_user, self.m_cab, M_PINFL, "m2")
        self.assertEqual(res.data["order"]["state"], "closed")
        # QR ochiq sahifa — ikki imzo, haqiqiy
        token = res.data["document"]["current_version"]["qr_token"]
        self.client.credentials()
        res = self.client.get(f"{BASE}/verify/{token}/")
        self.assertEqual((res.status_code, res.data["status"], res.data["doc_type"], len(res.data["signatures"])), (200, "valid", "act", 2))

    def test_return_and_revise_via_api(self):
        act_id = self.create_act([(self.l_ash.pk, "60")]).data["id"]
        self.attach(act_id)
        self.sign(act_id, self.s_user, self.s_cab, S_PINFL, "s1")
        res = self.as_(self.m_user, self.m_cab).post(f"{BASE}/acts/{act_id}/return/", {"reason_code": "quantity", "comment": "50 келди"},
                                                      format="json", HTTP_IDEMPOTENCY_KEY="r1")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data["status"], res.data["last_return"]["reason_code"]), ("returned", "quantity"))
        res = self.as_(self.s_user, self.s_cab).get(f"{BASE}/acts/", {"status": "returned"})
        self.assertEqual(res.data["count"], 1)
        res = self.client.patch(f"{BASE}/acts/{act_id}/", {"delivery_date": "2027-01-14", "responsible": "И.", "note": "Тузатилди",
                                                           "lines": [{"order_line": str(self.l_ash.pk), "qty": "50"}]}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data["status"], res.data["version_no"], len(res.data["versions"])), ("draft", 2, 2))
        self.assertEqual(res.data["versions"][1]["superseded_at"] is not None, True)
        res = self.client.get(f"{BASE}/acts/{act_id}/")
        self.assertEqual(res.data["attachments"], [])  # yangi versiya — yangi dalil kerak
        self.attach(act_id)
        self.sign(act_id, self.s_user, self.s_cab, S_PINFL, "s2")
        res = self.sign(act_id, self.m_user, self.m_cab, M_PINFL, "m2")
        self.assertEqual((res.status_code, res.data["status"]), (200, "approved"))

    def test_validation_errors_follow_contract(self):
        res = self.create_act([(self.l_ash.pk, "101")])
        self.assertEqual((res.status_code, res.data["error_code"], res.data["field"], res.data["index"]), (422, "qty_exceeds_remaining", "lines", 0))
        res = self.create_act([(self.l_ash.pk, "10")], key="c2", delivery_date="2027-01-20")
        self.assertEqual((res.status_code, res.data["error_code"]), (422, "delivery_date_invalid"))
        res = self.create_act([(self.l_ash.pk, "10")], key="c3", delivery_date="14.01.2027")
        self.assertEqual((res.status_code, res.data["error_code"]), (400, "validation"))
        res = self.create_act([], key="c4")
        self.assertEqual((res.status_code, res.data["error_code"]), (422, "lines_required"))
        res = self.as_(self.m_user, self.m_cab).post(f"{BASE}/orders/{self.order.pk}/acts/", {"delivery_date": "2027-01-14", "lines": []},
                                                      format="json", HTTP_IDEMPOTENCY_KEY="c5")
        self.assertEqual(res.status_code, 403)

    def test_cancel_draft_and_attachment_rules(self):
        act_id = self.create_act([(self.l_ash.pk, "60")]).data["id"]
        res = self.client.post(f"{BASE}/acts/{act_id}/attachments/", {"file": SimpleUploadedFile("x.txt", b"hello", content_type="text/plain")}, format="multipart")
        self.assertEqual((res.status_code, res.data["error_code"]), (400, "invalid_file"))
        att = self.attach(act_id).data
        res = self.client.delete(f"{BASE}/acts/{act_id}/attachments/{att['id']}/")
        self.assertEqual(res.status_code, 204)
        res = self.client.post(f"{BASE}/acts/{act_id}/cancel/", {"comment": "Нотўғри"}, format="json", HTTP_IDEMPOTENCY_KEY="x1")
        self.assertEqual((res.status_code, res.data["status"]), (200, "cancelled"))
        res = self.client.get(f"{BASE}/orders/{self.order.pk}/")
        self.assertEqual(res.data["actions"], ["create_act"])


class ActScopeApiTest(ActApiBase):
    def test_scope_other_mahalla_observer_union(self):
        act_id = self.create_act([(self.l_ash.pk, "60")]).data["id"]
        self.attach(act_id)
        self.sign(act_id, self.s_user, self.s_cab, S_PINFL, "s1")
        res = self.as_(self.x_user, self.x_cab).get(f"{BASE}/acts/{act_id}/")
        self.assertEqual(res.status_code, 404)
        res = self.as_(self.o_user, self.o_cab).get(f"{BASE}/acts/")
        self.assertEqual((res.status_code, res.data["count"]), (200, 1))
        self.assertEqual(res.data["results"][0]["actions"], [])
        res = self.as_(self.u_user, self.u_cab).get(f"{BASE}/acts/{act_id}/")
        self.assertEqual(res.status_code, 200)
        res = self.client.post(f"{BASE}/acts/{act_id}/return/", {"reason_code": "quantity", "comment": "x"}, format="json", HTTP_IDEMPOTENCY_KEY="u1")
        self.assertEqual(res.status_code, 403)
        res = self.as_(self.x_user, self.x_cab).post(f"{BASE}/acts/{act_id}/sign-task/", {}, format="json")
        self.assertEqual(res.status_code, 404)
