"""Umumiy hujjat imzosi: challenge va document rejimlari, imzolovchi tekshiruvi (TZ §13.1; Q05, Q06)."""
import json
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.yashil.models import Order, OrderLine, Signature, YashilMembership
from apps.yashil.services import signing
from apps.yashil.services.documents import build_order_form
from apps.yashil.services.signing import SigningError
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_item, make_mahalla, make_region, make_user, member,
)
from apps.yashil.tests._eimzo import PINFL, TIN, FakeEimzo, fake_sign


class SigningTest(TestCase):
    def setUp(self):
        cache.clear()
        d = make_district(make_region())
        self.mahalla = make_mahalla(d)
        self.forest = make_forest()
        assign_forest(self.mahalla, self.forest)
        self.user = make_user("m", role="ym_mahalla", pinfl=PINFL)
        self.cab = member(self.user, YashilMembership.MemberType.MAHALLA, mahalla=self.mahalla)
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest,
                                          created_by_membership=self.cab, title="Кўчат", address="A",
                                          lat=Decimal("41.3"), lon=Decimal("69.24"), area_ha=Decimal("0.5"))
        OrderLine.objects.create(order=self.order, catalog_item=make_item("ASH", "Шумтол", "forest", "seedling", "tup"), qty=Decimal("10"))
        self.version = build_order_form(self.order, self.cab)
        self.request = APIRequestFactory().post("/x")

    def prepare(self, eimzo):
        with patch.object(signing, "eimzo_api", eimzo):
            return signing.prepare_signing(self.version, self.user, self.cab, Signature.Role.MAHALLA, self.request)

    def verify(self, eimzo, pkcs7, nonce):
        with patch.object(signing, "eimzo_api", eimzo):
            return signing.verify_and_store(self.version, self.user, self.cab, Signature.Role.MAHALLA, pkcs7, nonce, self.request)

    def test_challenge_mode_when_vpn_down(self):
        e = FakeEimzo(vpn_up=False)
        ch = self.prepare(e)
        self.assertEqual(ch["mode"], "challenge")
        self.assertEqual(ch["sign_text"], FakeEimzo.CHALLENGE)
        sig = self.verify(e, fake_sign(FakeEimzo.CHALLENGE), ch["nonce"])
        self.assertTrue(sig.is_valid)
        self.assertEqual((sig.signer_pinfl, sig.signer_tin, sig.mode), (PINFL, TIN, "challenge"))
        self.version.refresh_from_db()
        self.assertEqual(self.version.status, "signed")
        self.assertEqual(sig.verify_result["content_hash"], self.version.content_hash)

    def test_document_mode_when_vpn_up(self):
        e = FakeEimzo(vpn_up=True)
        ch = self.prepare(e)
        self.assertEqual(ch["mode"], "document")
        payload = json.loads(ch["sign_text"])
        self.assertEqual(payload["content_hash"], self.version.content_hash)
        sig = self.verify(e, fake_sign(ch["sign_text"]), ch["nonce"])
        self.assertEqual(sig.mode, "document")
        self.assertTrue(sig.verify_result["timestamped"])

    def test_wrong_challenge_text_is_rejected(self):
        e = FakeEimzo()
        ch = self.prepare(e)
        with self.assertRaises(SigningError) as cm:
            self.verify(e, fake_sign("boshqa matn"), ch["nonce"])
        self.assertEqual(cm.exception.code, "signature_invalid")
        self.assertFalse(Signature.objects.exists())

    def test_pinfl_mismatch_is_rejected(self):
        e = FakeEimzo(pinfl="99999999999999")
        ch = self.prepare(e)
        with self.assertRaises(SigningError) as cm:
            self.verify(e, fake_sign(FakeEimzo.CHALLENGE), ch["nonce"])
        self.assertEqual(cm.exception.code, "signer_mismatch")

    def test_user_without_pinfl_cannot_sign(self):
        self.user.pinfl = None; self.user.save()
        with self.assertRaises(SigningError) as cm:
            self.prepare(FakeEimzo())
        self.assertEqual(cm.exception.code, "signer_profile")

    def test_cannot_sign_without_permission(self):
        self.cab.can_sign = False; self.cab.save()
        with self.assertRaises(SigningError) as cm:
            self.prepare(FakeEimzo())
        self.assertEqual(cm.exception.code, "cannot_sign")

    def test_challenge_is_single_use_and_nonce_bound(self):
        e = FakeEimzo()
        ch = self.prepare(e)
        self.verify(e, fake_sign(FakeEimzo.CHALLENGE), ch["nonce"])
        with self.assertRaises(SigningError):
            self.verify(e, fake_sign(FakeEimzo.CHALLENGE), ch["nonce"])

    def test_tampered_content_after_prepare_is_rejected(self):
        e = FakeEimzo()
        ch = self.prepare(e)
        self.version.content["number"] = "YM-9999-999999"
        self.version.content_hash = ""; self.version.save()
        with self.assertRaises(SigningError) as cm:
            self.verify(e, fake_sign(FakeEimzo.CHALLENGE), ch["nonce"])
        self.assertEqual(cm.exception.code, "content_changed")
