"""Qabul sinovlari (TZ §18–19): alohida tekshirilmagan holatlar — Q12 parallel qabul, Q25 buzilgan hujjat,
Q26 tashqi xizmat uzilishi, Q29 o'g'it katalogi, Q33 ruxsatsiz fayl, Q34 qabul o'rtasida baza xatosi."""
import shutil
import tempfile
import threading
from decimal import Decimal
from unittest.mock import patch

import requests
from django.db import DatabaseError, connection
from django.test import TransactionTestCase, override_settings

from apps.yashil.models import (
    Acceptance, DocumentVersion, Order, OrderEvent, OrderState, Signature, StockMovement,
)
from apps.yashil.services import ledger, signing
from apps.yashil.services import transitions as tr
from apps.yashil.services.integrity import version_problems
from apps.yashil.tests._eimzo import FakeEimzo, fake_sign
from apps.yashil.tests.test_ledger import NOW, LedgerBase
from apps.yashil.tests.test_order_api import OrderApiBase
from apps.yashil.tests._common import BASE


class ConcurrentAcceptanceTest(TransactionTestCase):
    """Q12: bir vaqtda ikki qabul — harakatlar yo'qolmaydi, bir buyurtma ikki marta ajratilmaydi."""

    setUp = LedgerBase.setUp
    order = LedgerBase.order
    opening = LedgerBase.opening

    def _run_parallel(self, jobs):
        barrier = threading.Barrier(len(jobs))
        results = [None] * len(jobs)

        def worker(i, order_id, cabinet):
            try:
                barrier.wait(timeout=10)
                tr.accept(Order.objects.get(pk=order_id), cabinet, executor_name="Иброҳимов")
                results[i] = "ok"
            except Exception as exc:  # noqa: BLE001 — natija sifatida qaytariladi
                results[i] = type(exc).__name__
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(i, o.pk, cab)) for i, (o, cab) in enumerate(jobs)]
        with patch("django.utils.timezone.now", return_value=NOW):
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30)
        return results

    def test_q12_two_orders_accepted_at_once_both_allocated_balance_negative(self):
        self.opening(self.fw, self.ash, "100")
        o1 = self.order([(self.ash, "60")], number="YM-2027-000001")
        o2 = self.order([(self.ash, "50")], number="YM-2027-000002")
        self.assertEqual(self._run_parallel([(o1, self.f_cab), (o2, self.f_cab)]), ["ok", "ok"])
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("-10"))
        for o in (o1, o2):
            o.refresh_from_db()
            self.assertEqual(o.state, OrderState.EXECUTION)
            self.assertEqual(StockMovement.objects.filter(kind="allocate", order_line__order=o).count(), 1)

    def test_q13_same_order_accepted_twice_at_once_allocates_once(self):
        self.opening(self.fw, self.ash, "100")
        o = self.order([(self.ash, "60")])
        results = self._run_parallel([(o, self.f_cab), (o, self.f_signer)])
        self.assertEqual(sorted(results), ["TransitionError", "ok"])
        self.assertEqual(Acceptance.objects.filter(order=o).count(), 1)
        self.assertEqual(StockMovement.objects.filter(kind="allocate").count(), 1)
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("40"))


class DatabaseErrorDuringAcceptanceTest(LedgerBase):
    def test_q34_failure_after_allocation_rolls_back_everything_and_retry_is_clean(self):
        self.opening(self.fw, self.ash, "100")
        o = self.order([(self.ash, "60")])
        with patch("apps.yashil.services.transitions._event", side_effect=DatabaseError("connection lost")):
            with self.assertRaises(DatabaseError):
                self.accept(o, self.f_cab)
        o.refresh_from_db()
        self.assertEqual(o.state, OrderState.SUPPLIER_REVIEW)
        self.assertIsNone(o.delivery_due)
        self.assertFalse(Acceptance.objects.filter(order=o).exists())
        self.assertEqual(StockMovement.objects.filter(kind="allocate").count(), 0)
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("100"))
        self.accept(o, self.f_cab)
        self.assertEqual(StockMovement.objects.filter(kind="allocate").count(), 1)
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("40"))


class ExternalServiceOutageTest(OrderApiBase):
    def test_q26_signing_service_down_then_retry_with_same_key_gives_one_submission(self):
        d = self.create_draft()
        with patch.object(signing, "eimzo_api", self.eimzo):
            doc = self.client.post(f"{BASE}/orders/{d['id']}/document/", {"version_no": 1}, format="json").data
        body = {"document_version_id": doc["document_version"]["id"], "nonce": doc["nonce"],
                "pkcs7": fake_sign(doc["sign_text"]), "version_no": 1}
        down = FakeEimzo()
        down.eri_backend_auth = lambda *a: (_ for _ in ()).throw(requests.ConnectionError("e-imzo down"))
        with patch.object(signing, "eimzo_api", down):
            res = self.client.post(f"{BASE}/orders/{d['id']}/submit/", body, format="json", HTTP_IDEMPOTENCY_KEY="s1")
        self.assertEqual((res.status_code, res.data["error_code"]), (503, "eimzo_unavailable"))
        self.assertEqual(Order.objects.get(pk=d["id"]).state, OrderState.DRAFT)
        self.assertEqual(Signature.objects.count(), 0)
        with patch.object(signing, "eimzo_api", self.eimzo):
            first = self.client.post(f"{BASE}/orders/{d['id']}/submit/", body, format="json", HTTP_IDEMPOTENCY_KEY="s1")
            again = self.client.post(f"{BASE}/orders/{d['id']}/submit/", body, format="json", HTTP_IDEMPOTENCY_KEY="s1")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual((again.status_code, again.data["state"], again.data["number"]), (200, "union_new", first.data["number"]))
        self.assertEqual(Signature.objects.count(), 1)
        self.assertEqual(OrderEvent.objects.filter(order_id=d["id"], action="submit").count(), 1)
        self.assertEqual(Order.objects.filter(mahalla=self.mahalla).count(), 1)


class FertilizerCatalogTest(OrderApiBase):
    def test_q29_fertilizer_only_in_dm_route(self):
        self.as_(self.m_user)
        forest_codes = {r["code"] for r in self.client.get(f"{BASE}/catalog/", {"supplier": str(self.forest.pk)}).data}
        dm_codes = {r["code"] for r in self.client.get(f"{BASE}/catalog/", {"supplier": str(self.dm.pk)}).data}
        self.assertEqual((forest_codes, dm_codes), ({"ASH", "MUL"}, {"BIO"}))
        res = self.client.post(f"{BASE}/orders/", self.draft_payload(lines=[{"catalog_item": str(self.bio.pk), "qty": "50"}]), format="json")
        self.assertEqual(res.status_code, 422, res.data)
        d = self.create_draft(route="dm", supplier_org=str(self.dm.pk), lines=[{"catalog_item": str(self.bio.pk), "qty": "50"}], base_seedlings=20)
        _, res = self.sign_and_submit(d["id"], 1)
        self.assertEqual((res.status_code, res.data["route"]), (200, "dm"))


class TamperedDocumentTest(OrderApiBase):
    def test_q25_changed_content_or_signature_hash_is_not_shown_as_valid(self):
        o = self.submitted_order()
        v = o.documents.get().current_version
        self.client.credentials()
        self.assertEqual(self.client.get(f"{BASE}/verify/{v.qr_token}/").data["status"], "valid")
        self.assertEqual(version_problems(v), [])
        content = dict(v.content, mahalla_name="Сохта маҳалла")
        DocumentVersion.objects.filter(pk=v.pk).update(content=content)
        res = self.client.get(f"{BASE}/verify/{v.qr_token}/")
        self.assertEqual(res.data["status"], "tampered")
        self.assertEqual([s["valid"] for s in res.data["signatures"]], [False])
        v.refresh_from_db()
        self.assertEqual(version_problems(v), ["content_hash"])
        # Mazmun tiklanadi, lekin imzo boshqa hash'ga bog'langan
        DocumentVersion.objects.filter(pk=v.pk).update(content=self._original_content)
        sig = v.signatures.get()
        sig.verify_result = dict(sig.verify_result, content_hash="0" * 64)
        sig.save(update_fields=["verify_result"])
        v.refresh_from_db()
        self.assertEqual(version_problems(v), ["signature_hash:mahalla"])
        self.assertEqual(self.client.get(f"{BASE}/verify/{v.qr_token}/").data["status"], "tampered")

    def submitted_order(self):
        o = super().submitted_order()
        self._original_content = o.documents.get().current_version.content
        return o


class ProtectedFileAndQrTest(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def test_q33_file_url_needs_valid_token_and_qr_shows_only_allowed_fields(self):
        with override_settings(MEDIA_ROOT=self.media, PROTECTED_MEDIA_SERVE_DIRECTLY=True):
            d = self.create_draft()
            res = self.client.post(f"{BASE}/orders/{d['id']}/attachments/", {"file": self._png(), "kind": "photo"}, format="multipart")
            self.assertEqual(res.status_code, 201, res.data)
            url = self.client.get(f"{BASE}/orders/{d['id']}/").data["attachments"][0]["url"]
            path, token = url.split("?t=")
            self.client.credentials()
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(self.client.get(path).status_code, 403)
            self.assertEqual(self.client.get(path + "?t=" + token[:-4] + "AAAA").status_code, 403)
            self.assertEqual(self.client.get(path.replace(".png", "-x.png") + "?t=" + token).status_code, 403)
            with patch("apps.general.protected_media.url_ttl", return_value=-1):
                self.assertEqual(self.client.get(url).status_code, 403)
        # QR sahifasi: shaxsiy ma'lumot, manzil, koordinata yo'q (TZ §13.2)
        o = self.submitted_order()
        v = o.documents.get().current_version
        self.client.credentials()
        res = self.client.get(f"{BASE}/verify/{v.qr_token}/")
        self.assertEqual(set(res.data), {"doc_type", "number", "version_no", "date", "status", "is_current", "is_partial",
                                         "order_number", "parties", "signatures", "missing_roles", "checked_at"})
        self.assertEqual(set(res.data["signatures"][0]), {"role", "signed_at", "valid"})
        text = str(res.data)
        for secret in ("41.311", "69.240", "марказий кўча", self.m_user.pinfl, self.m_user.email, "RAIS TEST"):
            self.assertNotIn(secret, text)

    @staticmethod
    def _png():
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile("joy.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png")
