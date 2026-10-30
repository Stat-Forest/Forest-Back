"""Dalolatnoma oqimi (TZ §10, §12, §22.2; Q16–Q19): yaratish, qoldiq hajm, ikki imzo, qaytarish, versiya, qisman/yakun."""
from datetime import date, datetime, timezone as tz
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.yashil.models import (
    Act,
    ActAttachment,
    Document,
    DocumentVersion,
    Order,
    OrderLine,
    OrderState,
    Signature,
    YashilMembership,
    YashilNotification,
)
from apps.yashil.services import acts as act_service
from apps.yashil.services import ledger, signing
from apps.yashil.services import transitions as tr
from apps.yashil.services.transitions import TransitionError
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_item, make_mahalla, make_region, make_union, make_user, member,
    route_union,
)
from apps.yashil.tests._eimzo import FakeEimzo, fake_sign

T = YashilMembership.MemberType
NOW = datetime(2027, 1, 11, 9, tzinfo=tz.utc)
LATER = datetime(2027, 1, 15, 9, tzinfo=tz.utc)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
M_PINFL, S_PINFL = "31234567890123", "55555555555555"


class ActBase(TestCase):
    def setUp(self):
        cache.clear()
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.forest = make_forest()
        assign_forest(self.mahalla, self.forest)
        self.unit = make_union(self.district); route_union(self.mahalla, self.unit)
        self.ash = make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup")
        self.mul = make_item("MUL", "Мульча", "forest", "mulch", "kg")
        self.m_user = make_user("m", role="ym_mahalla", pinfl=M_PINFL)
        self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla, position_title="Раис")
        self.u_user = make_user("u", role="ym_union"); self.u_cab = member(self.u_user, T.UNION, union_unit=self.unit, can_sign=False)
        self.s_user = make_user("s", role="tashkilot_rahbari", organization=self.forest, pinfl=S_PINFL)
        self.s_cab = member(self.s_user, T.SUPPLIER, organization=self.forest, position_title="Директор")
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest, union_unit=self.unit,
                                          created_by_membership=self.m_cab, title="Кўчат", address="Боғистон", number="YM-2027-000001",
                                          state=OrderState.SUPPLIER_REVIEW, lat=Decimal("41.3"), lon=Decimal("69.2"), area_ha=Decimal("0.5"),
                                          first_submitted_at=datetime(2027, 1, 5, 9, tzinfo=tz.utc))
        self.l_ash = OrderLine.objects.create(order=self.order, catalog_item=self.ash, qty=Decimal("100"))
        self.l_mul = OrderLine.objects.create(order=self.order, catalog_item=self.mul, qty=Decimal("50"))
        with patch("django.utils.timezone.now", return_value=NOW):
            tr.accept(self.order, self.s_cab, executor_name="Иброҳимов")
        self.request = APIRequestFactory().post("/x")

    def lines(self, ash=None, mul=None):
        out = []
        if ash is not None:
            out.append({"order_line": self.l_ash, "qty": Decimal(ash)})
        if mul is not None:
            out.append({"order_line": self.l_mul, "qty": Decimal(mul)})
        return out

    def create(self, ash=None, mul=None, when=LATER, delivery_date=date(2027, 1, 14), **kw):
        with patch("django.utils.timezone.now", return_value=when):
            return act_service.create_act(self.order, self.s_cab, delivery_date=delivery_date, lines=self.lines(ash, mul),
                                          responsible="Иброҳимов", note=kw.pop("note", ""), **kw)

    def attach(self, act):
        return ActAttachment.objects.create(act=act, version_no=act.version_no, file=SimpleUploadedFile("f.png", PNG, content_type="image/png"),
                                            original_name="f.png", size=len(PNG), kind="photo", uploaded_by=self.s_user)

    def sign(self, act, cabinet, pinfl, when=LATER):
        e = FakeEimzo(pinfl=pinfl)
        with patch.object(signing, "eimzo_api", e), patch("django.utils.timezone.now", return_value=when):
            task = act_service.sign_task(act, cabinet, self.request)
            return act_service.sign(act, cabinet, pkcs7=fake_sign(task["sign_text"]), nonce=task["nonce"], request=self.request)

    def supplier_sign(self, act, when=LATER):
        return self.sign(act, self.s_cab, S_PINFL, when)

    def mahalla_sign(self, act, when=LATER):
        return self.sign(act, self.m_cab, M_PINFL, when)


class CreateActTest(ActBase):
    def test_creates_numbered_act_with_version_lines_and_partial_flag(self):
        act = self.create(ash="60")
        self.assertEqual((act.number, act.index, act.status, act.version_no, act.is_partial), ("YM-2027-000001/A1", 1, "draft", 1, True))
        v = act.current_version
        self.assertEqual([(l.order_line_id, l.qty) for l in v.lines.all()], [(self.l_ash.id, Decimal("60"))])
        self.assertEqual(v.snapshot["lines"][0]["name_cyr"], "Шумтол кўчати")
        self.assertEqual(v.delivery_date, date(2027, 1, 14))
        self.assertEqual(self.order.events.filter(action="act_create").count(), 1)

    def test_only_one_open_act_per_order(self):
        self.create(ash="60")
        with self.assertRaises(TransitionError) as cm:
            self.create(ash="10")
        self.assertEqual((cm.exception.code, cm.exception.status), ("act_in_progress", 409))

    def test_q19_quantity_cannot_exceed_remaining(self):
        with self.assertRaises(TransitionError) as cm:
            self.create(ash="101")
        self.assertEqual((cm.exception.code, cm.exception.field, cm.exception.index), ("qty_exceeds_remaining", "lines", 0))
        with self.assertRaises(TransitionError) as cm:
            self.create(ash="0")
        self.assertEqual(cm.exception.code, "invalid_qty")
        with self.assertRaises(TransitionError) as cm:
            self.create()
        self.assertEqual(cm.exception.code, "lines_required")

    def test_delivery_date_not_in_future_and_not_before_acceptance(self):
        with self.assertRaises(TransitionError) as cm:
            self.create(ash="10", delivery_date=date(2027, 1, 16))
        self.assertEqual(cm.exception.code, "delivery_date_invalid")
        with self.assertRaises(TransitionError) as cm:
            self.create(ash="10", delivery_date=date(2027, 1, 10))
        self.assertEqual(cm.exception.code, "delivery_date_invalid")

    def test_only_supplier_of_order_in_execution_creates(self):
        with self.assertRaises(TransitionError) as cm:
            with patch("django.utils.timezone.now", return_value=LATER):
                act_service.create_act(self.order, self.m_cab, delivery_date=date(2027, 1, 14), lines=self.lines(ash="10"), responsible="x", note="")
        self.assertEqual(cm.exception.status, 403)
        Order.objects.filter(pk=self.order.pk).update(state=OrderState.SUPPLIER_REVIEW)
        self.order.refresh_from_db()
        with self.assertRaises(TransitionError) as cm:
            self.create(ash="10")
        self.assertEqual(cm.exception.code, "state_conflict")


class SignAndApproveTest(ActBase):
    def test_supplier_signature_needs_evidence_and_sends_to_mahalla(self):
        act = self.create(ash="60")
        with self.assertRaises(TransitionError) as cm:
            with patch("django.utils.timezone.now", return_value=LATER):
                act_service.sign_task(act, self.s_cab, self.request)
        self.assertEqual(cm.exception.code, "evidence_required")
        self.attach(act)
        with self.assertRaises(TransitionError) as cm:
            self.mahalla_sign(act)  # mahalla hali imzolay olmaydi — akt ko'rib chiqishda emas
        self.assertEqual(cm.exception.status, 403)
        self.supplier_sign(act)
        act.refresh_from_db()
        self.assertEqual(act.status, "mahalla_review")
        dv = act.current_version.document_version
        self.assertEqual((dv.document.kind, dv.document.number, dv.status), ("act", "YM-2027-000001/A1", "partly_signed"))
        self.assertEqual(dv.content["date"], "15.01.2027")
        self.assertEqual(list(dv.signatures.values_list("role", flat=True)), ["supplier"])
        self.assertIn("TOPSHIRISH", dv.html)
        self.assertEqual(YashilNotification.objects.filter(kind="act_sent", recipient_user=self.m_user).count(), 1)
        # ombor o'zgarmagan (Q16)
        self.assertEqual(ledger.balance(ledger.default_warehouse(self.forest), self.ash), Decimal("-100"))

    def test_q16_q19_mahalla_approval_counts_quantities_without_stock_change_and_closes_when_complete(self):
        a1 = self.create(ash="60"); self.attach(a1); self.supplier_sign(a1)
        self.mahalla_sign(a1)
        a1.refresh_from_db(); self.order.refresh_from_db()
        self.assertEqual((a1.status, self.order.state), ("approved", "partial"))
        dv = a1.current_version.document_version
        self.assertEqual((dv.status, sorted(dv.signatures.values_list("role", flat=True))), ("signed", ["mahalla", "supplier"]))
        self.assertEqual(act_service.accepted_by_line(self.order), {self.l_ash.id: Decimal("60"), self.l_mul.id: Decimal("0")})
        self.assertEqual(ledger.balance(ledger.default_warehouse(self.forest), self.ash), Decimal("-100"))
        self.assertEqual(YashilNotification.objects.filter(kind="act_approved", recipient_user=self.s_user).count(), 1)
        # ikkinchi partiya — yangi raqam /A2; 41 oshib ketadi (60+41 > 100)
        with self.assertRaises(TransitionError) as cm:
            self.create(ash="41", mul="50")
        self.assertEqual(cm.exception.code, "qty_exceeds_remaining")
        a2 = self.create(ash="40", mul="50"); self.attach(a2)
        self.assertEqual((a2.number, a2.is_partial), ("YM-2027-000001/A2", False))
        self.supplier_sign(a2); self.mahalla_sign(a2)
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, "closed")
        self.assertIsNotNone(self.order.closed_at)
        self.assertEqual(self.order.events.filter(action="act_approve").count(), 2)

    def test_approval_rechecks_remaining_and_is_idempotent(self):
        a1 = self.create(ash="60"); self.attach(a1); self.supplier_sign(a1)
        self.mahalla_sign(a1)
        with self.assertRaises(TransitionError) as cm:
            self.mahalla_sign(a1)
        self.assertEqual(cm.exception.status, 409)

    def test_signature_of_wrong_person_is_rejected(self):
        act = self.create(ash="60"); self.attach(act)
        with self.assertRaises(signing.SigningError) as cm:
            self.sign(act, self.s_cab, M_PINFL)
        self.assertEqual(cm.exception.code, "signer_mismatch")
        act.refresh_from_db()
        self.assertEqual(act.status, "draft")


class ReturnAndReviseTest(ActBase):
    def test_q17_q18_return_then_revise_creates_v2_and_old_version_is_superseded(self):
        act = self.create(ash="60"); self.attach(act); self.supplier_sign(act)
        with self.assertRaises(TransitionError) as cm:
            act_service.return_act(act, self.m_cab, reason_code="quantity", comment="")
        self.assertEqual(cm.exception.code, "comment_required")
        with patch("django.utils.timezone.now", return_value=LATER):
            act_service.return_act(act, self.m_cab, reason_code="quantity", comment="50 туп келди")
        act.refresh_from_db()
        self.assertEqual(act.status, "returned")
        self.assertEqual(act_service.accepted_by_line(self.order)[self.l_ash.id], Decimal("0"))  # Q17
        self.assertEqual(YashilNotification.objects.filter(kind="act_returned", recipient_user=self.s_user).count(), 1)
        self.assertEqual(ledger.balance(ledger.default_warehouse(self.forest), self.ash), Decimal("-100"))
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, "execution")
        v1 = act.current_version
        old_dv = v1.document_version
        with patch("django.utils.timezone.now", return_value=LATER):
            act_service.update_act(act, self.s_cab, delivery_date=date(2027, 1, 14), lines=self.lines(ash="50"), responsible="Иброҳимов", note="Тузатилди")
        act.refresh_from_db(); v1.refresh_from_db(); old_dv.refresh_from_db()
        self.assertEqual((act.status, act.version_no, act.number), ("draft", 2, "YM-2027-000001/A1"))
        self.assertIsNotNone(v1.superseded_at)
        self.assertEqual(old_dv.status, "superseded")
        self.assertEqual(old_dv.signatures.count(), 1)  # eski imzo saqlanadi
        self.assertEqual(act.current_version.lines.get().qty, Decimal("50"))
        self.assertEqual(act.versions.count(), 2)
        self.attach(act); self.supplier_sign(act); self.mahalla_sign(act)
        act.refresh_from_db()
        self.assertEqual((act.status, act.current_version.document_version.version_no), ("approved", 2))
        self.assertEqual(act_service.accepted_by_line(self.order)[self.l_ash.id], Decimal("50"))

    def test_draft_update_replaces_lines_in_place_and_cancel_closes_act(self):
        act = self.create(ash="60")
        with patch("django.utils.timezone.now", return_value=LATER):
            act_service.update_act(act, self.s_cab, delivery_date=date(2027, 1, 13), lines=self.lines(ash="30", mul="10"), responsible="Х", note="")
        act.refresh_from_db()
        self.assertEqual((act.version_no, act.versions.count(), act.current_version.lines.count()), (1, 1, 2))
        self.assertEqual(act.current_version.delivery_date, date(2027, 1, 13))
        with patch("django.utils.timezone.now", return_value=LATER):
            act_service.cancel_act(act, self.s_cab, comment="Нотўғри")
        act.refresh_from_db()
        self.assertEqual(act.status, "cancelled")
        a2 = self.create(ash="60")  # endi yangi akt yaratish mumkin
        self.assertEqual(a2.number, "YM-2027-000001/A2")

    def test_mahalla_cannot_return_draft_and_supplier_cannot_return(self):
        act = self.create(ash="60")
        with self.assertRaises(TransitionError) as cm:
            act_service.return_act(act, self.m_cab, reason_code="quantity", comment="x")
        self.assertEqual(cm.exception.code, "state_conflict")
        self.attach(act); self.supplier_sign(act)
        with self.assertRaises(TransitionError) as cm:
            act_service.return_act(act, self.s_cab, reason_code="quantity", comment="x")
        self.assertEqual(cm.exception.status, 403)

    def test_allowed_actions_per_role_and_state(self):
        act = self.create(ash="60")
        self.assertEqual(act_service.allowed_act_actions(act, self.s_cab), ["edit", "attach", "sign", "cancel"])
        self.assertEqual(act_service.allowed_act_actions(act, self.m_cab), [])
        self.assertEqual(tr.allowed_actions(self.order, self.s_cab), [])  # ochiq akt bor — yangi yaratilmaydi
        self.attach(act); self.supplier_sign(act); act.refresh_from_db()
        self.assertEqual(act_service.allowed_act_actions(act, self.m_cab), ["approve", "return"])
        self.assertEqual(act_service.allowed_act_actions(act, self.s_cab), [])
        self.assertEqual(act_service.allowed_act_actions(act, self.u_cab), [])
        self.mahalla_sign(act); act.refresh_from_db()
        self.assertEqual(act_service.allowed_act_actions(act, self.m_cab), [])
        self.order.refresh_from_db()
        self.assertEqual(tr.allowed_actions(self.order, self.s_cab), ["create_act", "cancel_request"])


class ActVerifyPayloadTest(ActBase):
    def test_q25_public_payload_shows_pending_then_valid_then_superseded(self):
        from apps.yashil.services.documents import public_verify_payload

        act = self.create(ash="60"); self.attach(act); self.supplier_sign(act)
        act.refresh_from_db()
        dv = act.current_version.document_version
        p = public_verify_payload(dv)
        self.assertEqual((p["doc_type"], p["status"], p["missing_roles"]), ("act", "pending_signature", ["mahalla"]))
        self.assertEqual(p["parties"], {"mahalla": "Bog'iston mahallasi", "supplier": "Namuna o'rmon xo'jaligi"})  # uz hujjat — lotin
        with patch("django.utils.timezone.now", return_value=LATER):
            act_service.return_act(act, self.m_cab, reason_code="quantity", comment="x")
            act_service.update_act(act, self.s_cab, delivery_date=date(2027, 1, 14), lines=self.lines(ash="50"), responsible="x", note="")
        dv.refresh_from_db()
        self.assertEqual(public_verify_payload(dv)["status"], "superseded")
        self.attach(act); self.supplier_sign(act); self.mahalla_sign(act)
        act.refresh_from_db()
        p = public_verify_payload(act.current_version.document_version)
        self.assertEqual((p["status"], p["missing_roles"], len(p["signatures"])), ("valid", [], 2))
        for secret in ("41.3", S_PINFL, M_PINFL):
            self.assertNotIn(secret, str(p))
