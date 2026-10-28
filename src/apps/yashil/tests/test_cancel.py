"""Bekor qilish (TZ §9.3, javob Е4): qabulgacha — mahalla o'zi; qabuldan keyin so'rov → ikkinchi tomon → uyushma; faqat yetkazilmagan qismga tiklash."""
from datetime import date, datetime, timezone as tz
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.yashil.models import (
    Act,
    ActAttachment,
    CancelRequest,
    Document,
    Order,
    OrderLine,
    OrderState,
    StockMovement,
    YashilMembership,
    YashilNotification,
)
from apps.yashil.services import acts as act_service
from apps.yashil.services import cancel as cancel_service
from apps.yashil.services import ledger, signing
from apps.yashil.services import transitions as tr
from apps.yashil.services.transitions import TransitionError
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


class CancelBase(APITestCase):
    def setUp(self):
        cache.clear()
        d = make_district(make_region())
        self.mahalla = make_mahalla(d)
        self.forest = make_forest(); assign_forest(self.mahalla, self.forest)
        self.unit = make_union(d); route_union(self.mahalla, self.unit)
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        self.mul = make_item("MUL", "Мульча", "forest", "mulch", "kg")
        self.m_user = make_user("m", role="ym_mahalla", pinfl=M_PINFL); self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla)
        self.u_user = make_user("u", role="ym_union"); self.u_cab = member(self.u_user, T.UNION, union_unit=self.unit, can_sign=False)
        self.s_user = make_user("s", role="tashkilot_rahbari", organization=self.forest, pinfl=S_PINFL)
        self.s_cab = member(self.s_user, T.SUPPLIER, organization=self.forest)
        self.wh = ledger.default_warehouse(self.forest)
        ledger.post_opening(self.wh, self.ash, Decimal("100"), self.s_cab, doc_number="ИНВ", doc_date=date(2026, 12, 31))
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest, union_unit=self.unit,
                                          created_by_membership=self.m_cab, title="Кўчат", address="A", number="YM-2027-000001",
                                          state=OrderState.SUPPLIER_REVIEW, lat=Decimal("41.3"), lon=Decimal("69.2"), area_ha=Decimal("1"))
        self.l_ash = OrderLine.objects.create(order=self.order, catalog_item=self.ash, qty=Decimal("100"))
        self.l_mul = OrderLine.objects.create(order=self.order, catalog_item=self.mul, qty=Decimal("50"))

    def accept(self):
        with patch("django.utils.timezone.now", return_value=NOW):
            tr.accept(self.order, self.s_cab, executor_name="И.")

    def approved_act(self, ash):
        from rest_framework.test import APIRequestFactory

        req = APIRequestFactory().post("/x")
        with patch("django.utils.timezone.now", return_value=LATER):
            act = act_service.create_act(self.order, self.s_cab, delivery_date=date(2027, 1, 14), lines=[{"order_line": self.l_ash, "qty": Decimal(ash)}])
        ActAttachment.objects.create(act=act, version_no=1, file=SimpleUploadedFile("f.png", PNG, content_type="image/png"),
                                     original_name="f.png", size=len(PNG), kind="photo", uploaded_by=self.s_user)
        for cab, pinfl in ((self.s_cab, S_PINFL), (self.m_cab, M_PINFL)):
            with patch.object(signing, "eimzo_api", FakeEimzo(pinfl=pinfl)), patch("django.utils.timezone.now", return_value=LATER):
                task = act_service.sign_task(act, cab, req)
                act_service.sign(act, cab, pkcs7=fake_sign(task["sign_text"]), nonce=task["nonce"], request=req)
        self.order.refresh_from_db()
        return act

    def kinds(self, user):
        """Bekor qilishga oid xabarlar (ijroga qabul xabari hisobga olinmaydi)."""
        return list(YashilNotification.objects.filter(recipient_user=user).exclude(kind="order_accepted").order_by("id").values_list("kind", flat=True))


class CancelBeforeAcceptanceTest(CancelBase):
    def test_mahalla_cancels_draft_without_stock_effect(self):
        Order.objects.filter(pk=self.order.pk).update(state=OrderState.RETURNED); self.order.refresh_from_db()
        with self.assertRaises(TransitionError):
            cancel_service.cancel_before_acceptance(self.order, self.s_cab, reason="x")
        cancel_service.cancel_before_acceptance(self.order, self.m_cab, reason="Керак эмас")
        self.assertEqual((self.order.state, self.order.closed_at is not None), ("cancelled", True))
        self.assertEqual(ledger.balance(self.wh, self.ash), Decimal("100"))
        self.assertEqual(self.order.events.get(action="cancel").comment, "Керак эмас")
        with self.assertRaises(TransitionError) as cm:
            cancel_service.cancel_before_acceptance(self.order, self.m_cab, reason="яна")
        self.assertEqual(cm.exception.code, "state_conflict")

    def test_cannot_self_cancel_after_acceptance(self):
        self.accept()
        with self.assertRaises(TransitionError) as cm:
            cancel_service.cancel_before_acceptance(self.order, self.m_cab, reason="x")
        self.assertEqual(cm.exception.code, "state_conflict")


class CancelAfterAcceptanceTest(CancelBase):
    def test_full_cancel_three_steps_releases_everything(self):
        self.accept()
        self.assertEqual(ledger.balance(self.wh, self.ash), Decimal("0"))
        req = cancel_service.request_cancel(self.order, self.m_cab, lines=[], reason="Ҳудуд ўзгарди")
        self.assertEqual((req.status, req.requested_by_party), ("requested", "mahalla"))
        self.assertEqual(self.kinds(self.s_user), ["cancel_requested"])
        self.assertEqual(tr.allowed_actions(self.order, self.s_cab), ["cancel_agree", "cancel_reject"])
        self.assertEqual(tr.allowed_actions(self.order, self.u_cab), [])
        with self.assertRaises(TransitionError) as cm:
            cancel_service.approve_cancel(req, self.u_cab)  # avval ikkinchi tomon kelishishi kerak
        self.assertEqual(cm.exception.code, "state_conflict")
        with self.assertRaises(TransitionError):
            cancel_service.agree_cancel(req, self.m_cab)  # so'rovchi o'zi kelisha olmaydi
        cancel_service.agree_cancel(req, self.s_cab)
        self.assertEqual(req.status, "agreed")
        self.assertEqual(self.kinds(self.u_user), ["cancel_requested", "cancel_agreed"])
        self.assertEqual(tr.allowed_actions(self.order, self.u_cab), ["cancel_approve", "cancel_reject"])
        self.assertEqual(ledger.balance(self.wh, self.ash), Decimal("0"))  # hali tiklanmagan
        with patch("django.utils.timezone.now", return_value=LATER):
            cancel_service.approve_cancel(req, self.u_cab)
        self.order.refresh_from_db()
        self.assertEqual((req.status, self.order.state), ("approved", "cancelled"))
        self.assertEqual(ledger.balance(self.wh, self.ash), Decimal("100"))
        self.assertEqual(ledger.balance(self.wh, self.mul), Decimal("0"))  # −50 + 50
        rel = StockMovement.objects.filter(kind="release")
        self.assertEqual(sorted(rel.values_list("qty", flat=True)), [Decimal("50"), Decimal("100")])
        doc = req.document
        self.assertEqual((doc.kind, doc.number), ("cancellation", "YM-2027-000001/B1"))
        self.assertEqual(doc.current_version.status, "signed")
        self.assertEqual(doc.current_version.content["result"], "cancelled")
        self.assertEqual(self.kinds(self.m_user), ["cancel_agreed", "cancel_approved"])
        self.assertEqual(self.kinds(self.s_user), ["cancel_requested", "cancel_approved"])

    def test_partial_cancel_releases_only_undelivered_part_and_shrinks_lines(self):
        self.accept()
        self.approved_act("60")  # 60 qabul qilingan, qoldi 40
        self.assertEqual(self.order.state, "partial")
        with self.assertRaises(TransitionError) as cm:
            cancel_service.request_cancel(self.order, self.s_cab, lines=[{"order_line": self.l_ash, "qty": Decimal("41")}], reason="x")
        self.assertEqual(cm.exception.code, "qty_exceeds_remaining")
        req = cancel_service.request_cancel(self.order, self.s_cab, lines=[{"order_line": self.l_ash, "qty": Decimal("40")}], reason="Кўчат тугади")
        self.assertEqual(req.requested_by_party, "supplier")
        self.assertEqual(self.kinds(self.m_user), ["act_sent", "cancel_requested"])
        cancel_service.agree_cancel(req, self.m_cab)
        with patch("django.utils.timezone.now", return_value=LATER):
            cancel_service.approve_cancel(req, self.u_cab)
        self.order.refresh_from_db(); self.l_ash.refresh_from_db()
        self.assertEqual(self.l_ash.qty, Decimal("60"))
        self.assertEqual(self.order.state, "partial")  # mulcha hali yetkazilmagan
        self.assertEqual(ledger.balance(self.wh, self.ash), Decimal("40"))  # 100 − 100 + 40
        self.assertEqual(ledger.balance(self.wh, self.mul), Decimal("-50"))
        self.assertEqual(req.document.current_version.content["lines"][0]["cancelled_qty"], "40")
        # Qolgan mulcha ham bekor qilinsa — buyurtma yopiladi (hamma qator qabul ≥ miqdor)
        req2 = cancel_service.request_cancel(self.order, self.m_cab, lines=[{"order_line": self.l_mul, "qty": Decimal("50")}], reason="Керак эмас")
        cancel_service.agree_cancel(req2, self.s_cab)
        with patch("django.utils.timezone.now", return_value=LATER):
            cancel_service.approve_cancel(req2, self.u_cab)
        self.order.refresh_from_db()
        self.assertEqual((self.order.state, req2.document.number), ("closed", "YM-2027-000001/B2"))
        self.assertEqual(ledger.balance(self.wh, self.mul), Decimal("0"))

    def test_open_act_or_pending_request_blocks_and_reject_path(self):
        self.accept()
        with patch("django.utils.timezone.now", return_value=LATER):
            act = act_service.create_act(self.order, self.s_cab, delivery_date=date(2027, 1, 14), lines=[{"order_line": self.l_ash, "qty": Decimal("10")}])
        with self.assertRaises(TransitionError) as cm:
            cancel_service.request_cancel(self.order, self.m_cab, lines=[], reason="x")
        self.assertEqual(cm.exception.code, "act_in_progress")
        with patch("django.utils.timezone.now", return_value=LATER):
            act_service.cancel_act(act, self.s_cab)
        with self.assertRaises(TransitionError) as cm:
            cancel_service.request_cancel(self.order, self.m_cab, lines=[], reason="")
        self.assertEqual(cm.exception.code, "reason_required")
        req = cancel_service.request_cancel(self.order, self.m_cab, lines=[], reason="x")
        with self.assertRaises(TransitionError) as cm:
            cancel_service.request_cancel(self.order, self.m_cab, lines=[], reason="y")
        self.assertEqual(cm.exception.code, "cancel_pending")
        with self.assertRaises(TransitionError) as cm:
            cancel_service.reject_cancel(req, self.s_cab, note="")
        self.assertEqual(cm.exception.code, "note_required")
        cancel_service.reject_cancel(req, self.s_cab, note="Етказилади")
        self.assertEqual(req.status, "rejected")
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, "execution")
        self.assertEqual(ledger.balance(self.wh, self.ash), Decimal("0"))
        self.assertEqual(self.kinds(self.m_user), ["cancel_rejected"])
        self.assertIn("create_act", tr.allowed_actions(self.order, self.s_cab))
        self.assertIn("cancel_request", tr.allowed_actions(self.order, self.m_cab))

    def test_union_can_reject_and_observer_cannot_touch(self):
        self.accept()
        req = cancel_service.request_cancel(self.order, self.m_cab, lines=[], reason="x")
        cancel_service.agree_cancel(req, self.s_cab)
        obs = member(make_user("o", role="ym_observer"), T.OBSERVER, can_prepare=False, can_sign=False)
        with self.assertRaises(TransitionError) as cm:
            cancel_service.approve_cancel(req, obs)
        self.assertEqual(cm.exception.status, 403)
        cancel_service.reject_cancel(req, self.u_cab, note="Асос етарли эмас")
        self.assertEqual((req.status, req.approved_by_id), ("rejected", self.u_cab.pk))


class CancelApiTest(CancelBase):
    def test_api_cycle(self):
        self.accept()
        auth(self.client, self.m_user, self.m_cab)
        res = self.client.post(f"{BASE}/orders/{self.order.pk}/cancel/", {"reason": "Ҳудуд ўзгарди", "lines": []}, format="json", HTTP_IDEMPOTENCY_KEY="c1")
        self.assertEqual(res.status_code, 201, res.data)
        req_id = res.data["id"]
        self.assertEqual(res.data["status"], "requested")
        res = self.client.get(f"{BASE}/orders/{self.order.pk}/")
        self.assertEqual(res.data["cancel_request"]["status"], "requested")
        self.assertEqual(res.data["actions"], [])
        self.client.credentials(); auth(self.client, self.s_user, self.s_cab)
        res = self.client.post(f"{BASE}/cancel/{req_id}/agree/", {}, format="json", HTTP_IDEMPOTENCY_KEY="c2")
        self.assertEqual((res.status_code, res.data["status"]), (200, "agreed"))
        self.client.credentials(); auth(self.client, self.u_user, self.u_cab)
        with patch("django.utils.timezone.now", return_value=LATER):
            res = self.client.post(f"{BASE}/cancel/{req_id}/approve/", {}, format="json", HTTP_IDEMPOTENCY_KEY="c3")
        self.assertEqual((res.status_code, res.data["status"], res.data["order"]["state"]), (200, "approved", "cancelled"))
        self.assertIsNotNone(res.data["document"])
        res = self.client.get(f"{BASE}/cancel/", {"order": str(self.order.pk)})
        self.assertEqual(res.data["count"], 1)
        token = res.data["results"][0]["document"]["current_version"]["qr_token"]
        self.client.credentials()
        res = self.client.get(f"{BASE}/verify/{token}/")
        self.assertEqual((res.data["doc_type"], res.data["status"]), ("cancellation", "valid"))

    def test_draft_cancel_via_api(self):
        Order.objects.filter(pk=self.order.pk).update(state=OrderState.DRAFT)
        auth(self.client, self.m_user, self.m_cab)
        res = self.client.post(f"{BASE}/orders/{self.order.pk}/cancel/", {"reason": "Керак эмас"}, format="json", HTTP_IDEMPOTENCY_KEY="d1")
        self.assertEqual((res.status_code, res.data["state"]), (200, "cancelled"))
        self.assertEqual(Document.objects.filter(kind="cancellation").count(), 0)
        self.assertFalse(CancelRequest.objects.exists())
