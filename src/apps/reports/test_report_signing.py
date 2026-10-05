import base64
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.reports.models import (
    Deadline, Report, ReportItem, ReportSignature, Statement, StatementColumn,
)
from apps.reports.services import report_signing

User = get_user_model()

BASE = "/api/v1/reports"
TIN = "305123456"
PINFL = "31234567890123"


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.text = json.dumps(data)

    def json(self):
        return self._data


def fake_sign(document: str) -> str:
    """Testda 'imzo' = hujjatning base64 matni (e-imzo-server soxtalashtiriladi)."""
    return base64.b64encode(document.encode("utf-8")).decode("ascii")


class FakeEimzo:
    """
    e-imzo-server o'rnini bosadi: timestamp pkcs7 ni o'zgartirmaydi, verify esa
    pkcs7 ichidagi hujjatni documentBase64 sifatida qaytaradi.
    """

    CHALLENGE = "9b573e40-cefd-42cc-a534-f6e78b27c2ae"

    def __init__(self, tin=TIN, pinfl=PINFL, status=1, verified=True, tsa_down=False, vpn_up=True):
        self.tin, self.pinfl, self.status, self.verified = tin, pinfl, status, verified
        self.tsa_down = tsa_down
        self.vpn_up = vpn_up
        self.timestamp_calls = 0

    def _subject(self):
        subject = {"CN": "RAHBAR TEST", report_signing.OID_PINFL: self.pinfl}
        if self.tin:
            subject[report_signing.OID_TIN] = self.tin
        return subject

    # ---- VPN'siz rejim ----
    def vpn_available(self, request):
        return self.vpn_up

    def eri_challenge(self, request):
        return True, 200, {"challenge": self.CHALLENGE, "ttl": 120, "status": 1}

    def eri_backend_auth(self, request, pkcs7):
        signed_text = base64.b64decode(pkcs7).decode("utf-8")
        if signed_text != self.CHALLENGE:
            return False, 200, "Challenge topilmadi yoki muddati o'tdi. Qaytadan urinib ko'ring."
        status = 1 if self.vpn_up else -1
        cert = {"serialNumber": "abc123", "validFrom": "2026-01-01 00:00:00", "validTo": "2027-01-01 00:00:00",
                # OCSP ishlamaganda subjectName bo'sh keladi (login'dagi kabi)
                "subjectName": self._subject() if self.vpn_up else {}}
        return True, 200, {"status": status, "subjectCertificateInfo": cert}

    def pkcs7_info(self, pkcs7, request):
        return 200, FakeResponse({"signers": [{"certificate": [{
            "subjectInfo": self._subject(), "serialNumber": "abc123",
            "validFrom": "2026-01-01 00:00:00", "validTo": "2027-01-01 00:00:00"}]}]})

    def timestamp_pkcs7(self, pkcs7, request):
        self.timestamp_calls += 1
        if self.tsa_down:
            return 400, FakeResponse({"status": -1, "message": "TimeStampTokenProvider UNAVAILABLE"}, 400)
        return 200, FakeResponse({"status": 1, "pkcs7b64": pkcs7, "message": ""})

    def eimzo_verify(self, pkcs7, request):
        subject = self._subject()
        return 200, FakeResponse({
            "status": self.status,
            "message": "" if self.status == 1 else "ЭЦП недействительна",
            "pkcs7Info": {
                "documentBase64": pkcs7,
                "signers": [{
                    "signingTime": "2026-10-05 12:00:00",
                    "verified": self.verified,
                    "certificateVerified": True,
                    "certificateValidAtSigningTime": True,
                    "timeStampInfo": {"time": "2026-10-05 12:00:05", "verified": True, "tsa": "test-tsa"},
                    "certificate": [{
                        "subjectInfo": subject,
                        "serialNumber": "abc123",
                        "validFrom": "2026-01-01 00:00:00",
                        "validTo": "2027-01-01 00:00:00",
                        "issuerName": "CN=TestCA",
                    }],
                }],
            },
        })


class ReportSigningTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        dept = Statement.objects.create(name="Bo'lim")
        cls.stmt = Statement.objects.create(name="Shakl", parent=dept)
        cls.org = Organization.objects.create(name="Tashkilot A", region="tashkent", stir=int(TIN))
        cls.org_no_stir = Organization.objects.create(name="Tashkilot B", region="tashkent")
        cls.deadline = Deadline.objects.create(statement=cls.stmt, submit_at="2026")
        cls.column = StatementColumn.objects.create(statement=cls.stmt, title="Amalda", ordering="1")

        cls.rahbar = User.objects.create_user(
            email="rahbar@example.com", password="TestPassword123!", first_name="R", last_name="A",
            role="tashkilot_rahbari", organization=cls.org, pinfl=PINFL,
        )
        cls.hodim = User.objects.create_user(
            email="hodim@example.com", password="TestPassword123!", first_name="H", last_name="A",
            role="tashkilot_hodimi", organization=cls.org,
        )

    def setUp(self):
        cache.clear()  # VPN holati va challenge'lar testlar orasida qolmasin
        self.report = Report.objects.create(organization=self.org, statement=self.stmt, deadline=self.deadline)
        self.item = ReportItem.objects.create(report=self.report, statement_column=self.column, value="10")
        self.client.force_authenticate(self.rahbar)

    def _challenge_full(self, report=None, eimzo=None):
        with patch.object(report_signing, "eimzo_api", eimzo or FakeEimzo()):
            resp = self.client.post(f"{BASE}/send/challenge/", {"id": str((report or self.report).id)}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def _challenge(self, report=None, eimzo=None):
        return self._challenge_full(report, eimzo)["document"]

    def _send(self, pkcs7, report=None, eimzo=None, nonce=None):
        body = {"id": str((report or self.report).id), "pkcs7": pkcs7}
        if nonce:
            body["nonce"] = nonce
        with patch.object(report_signing, "eimzo_api", eimzo or FakeEimzo()):
            return self.client.post(f"{BASE}/send/", body, format="json")

    def _assert_not_sent(self):
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Report.StatusChoices.SAVED)
        self.assertFalse(ReportSignature.objects.filter(report=self.report).exists())

    # ---------------- muvaffaqiyatli oqim ----------------

    def test_full_flow_sign_send_and_public_verify(self):
        document = self._challenge()
        payload = json.loads(document)
        self.assertEqual(payload["report_id"], str(self.report.id))
        self.assertEqual(payload["organization"]["stir"], TIN)

        resp = self._send(fake_sign(document))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Report.StatusChoices.SENT)
        self.assertEqual(self.report.sent_by, self.rahbar)

        sig = ReportSignature.objects.get(report=self.report)
        self.assertEqual(resp.json()["signature_id"], str(sig.id))
        self.assertTrue(sig.is_valid)
        self.assertEqual(sig.signer_tin, TIN)
        self.assertEqual(sig.signer_cn, "RAHBAR TEST")
        self.assertEqual(timezone.localtime(sig.signed_at).strftime("%H:%M:%S"), "12:00:05")  # TSA vaqti
        self.assertTrue(sig.verify_result["timestamped"])
        self.assertNotIn("OCSPResponse", json.dumps(sig.verify_result))

        # Ro'yxatda imzo ko'rinadi
        listed = self.client.get(f"{BASE}/").json()
        rows = listed.get("results", listed)
        row = next(r for r in rows if r["id"] == str(self.report.id))
        self.assertEqual(row["signature"]["id"], str(sig.id))
        self.assertEqual(row["signature"]["verify_path"], f"/verify/{sig.id}")

        # Ochiq tekshirish sahifasi (login'siz)
        self.client.force_authenticate(None)
        verify = self.client.get(f"{BASE}/signatures/{sig.id}/verify/")
        self.assertEqual(verify.status_code, 200, verify.content)
        body = verify.json()
        self.assertTrue(body["valid"])
        self.assertTrue(body["report_unchanged"])
        self.assertEqual(body["signer"]["full_name"], "RAHBAR TEST")
        self.assertEqual(body["signer"]["pinfl_masked"], "**********0123")
        self.assertEqual(body["report"]["status"], "sent")

        # Hisobot imzodan keyin o'zgartirilsa — ko'rinadi
        self.item.value = "999"
        self.item.save()
        self.assertFalse(self.client.get(f"{BASE}/signatures/{sig.id}/verify/").json()["report_unchanged"])

    def test_tsa_down_signature_still_accepted_without_timestamp(self):
        """TSA ulanmasa imzo tamg'asiz qabul qilinadi, signed_at = server vaqti."""
        document = self._challenge()
        eimzo = FakeEimzo(tsa_down=True)
        before = timezone.now()
        resp = self._send(fake_sign(document), eimzo=eimzo)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(eimzo.timestamp_calls, 2)  # bitta qayta urinish
        sig = ReportSignature.objects.get(report=self.report)
        self.assertFalse(sig.verify_result["timestamped"])
        self.assertGreaterEqual(sig.signed_at, before)
        self.client.force_authenticate(None)
        self.assertFalse(self.client.get(f"{BASE}/signatures/{sig.id}/verify/").json()["timestamped"])

    def test_tsa_down_rejected_when_timestamp_required(self):
        document = self._challenge()
        with self.settings(EIMZO_REQUIRE_TIMESTAMP=True):
            resp = self._send(fake_sign(document), eimzo=FakeEimzo(tsa_down=True))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("vaqt tamg", resp.content.decode())
        self._assert_not_sent()

    # ---------------- VPN'siz (challenge) rejim ----------------

    def test_vpn_down_uses_challenge_mode_and_backend_auth(self):
        eimzo = FakeEimzo(vpn_up=False)
        ch = self._challenge_full(eimzo=eimzo)
        self.assertEqual(ch["mode"], "challenge")
        self.assertEqual(ch["sign_text"], FakeEimzo.CHALLENGE)
        self.assertNotEqual(ch["sign_text"], ch["document"])

        resp = self._send(fake_sign(ch["sign_text"]), eimzo=eimzo, nonce=ch["nonce"])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Report.StatusChoices.SENT)

        sig = ReportSignature.objects.get(report=self.report)
        self.assertEqual(sig.verify_result["mode"], "challenge")
        self.assertFalse(sig.verify_result["ocsp_checked"])
        self.assertEqual(sig.verify_result["challenge"], FakeEimzo.CHALLENGE)
        self.assertEqual(sig.signer_tin, TIN)
        self.assertEqual(sig.signer_cn, "RAHBAR TEST")  # subjectName bo'sh -> pkcs7/info dan
        self.assertEqual(json.loads(sig.document)["report_id"], str(self.report.id))

        self.client.force_authenticate(None)
        body = self.client.get(f"{BASE}/signatures/{sig.id}/verify/").json()
        self.assertEqual(body["mode"], "challenge")
        self.assertFalse(body["ocsp_checked"])
        self.assertTrue(body["valid"])

    def test_vpn_up_uses_document_mode(self):
        ch = self._challenge_full()
        self.assertEqual(ch["mode"], "document")
        self.assertEqual(ch["sign_text"], ch["document"])

    def test_challenge_mode_wrong_signed_text_is_rejected(self):
        eimzo = FakeEimzo(vpn_up=False)
        ch = self._challenge_full(eimzo=eimzo)
        resp = self._send(fake_sign("boshqa matn"), eimzo=eimzo, nonce=ch["nonce"])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Challenge", resp.content.decode())
        self._assert_not_sent()

    def test_challenge_mode_without_nonce_is_rejected(self):
        eimzo = FakeEimzo(vpn_up=False)
        ch = self._challenge_full(eimzo=eimzo)
        resp = self._send(fake_sign(ch["sign_text"]), eimzo=eimzo)  # nonce yo'q
        self.assertEqual(resp.status_code, 400)
        self._assert_not_sent()

    def test_challenge_mode_report_changed_is_rejected(self):
        eimzo = FakeEimzo(vpn_up=False)
        ch = self._challenge_full(eimzo=eimzo)
        self.item.value = "12"
        self.item.save()
        resp = self._send(fake_sign(ch["sign_text"]), eimzo=eimzo, nonce=ch["nonce"])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("o'zgartirilgan", resp.content.decode())
        self._assert_not_sent()

    def test_challenge_mode_tin_mismatch_is_rejected(self):
        eimzo = FakeEimzo(vpn_up=False, tin="999999999")
        ch = self._challenge_full(eimzo=eimzo)
        resp = self._send(fake_sign(ch["sign_text"]), eimzo=eimzo, nonce=ch["nonce"])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("STIR", resp.content.decode())
        self._assert_not_sent()

    def test_challenge_is_single_use(self):
        document = self._challenge()
        self.assertEqual(self._send(fake_sign(document)).status_code, 200)
        Report.objects.filter(id=self.report.id).update(status=Report.StatusChoices.SAVED)
        resp = self._send(fake_sign(document))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(ReportSignature.objects.filter(report=self.report).count(), 1)

    # ---------------- rad etiladigan holatlar ----------------

    def test_send_without_pkcs7_is_rejected(self):
        resp = self.client.post(f"{BASE}/send/", {"id": str(self.report.id)}, format="json")
        self.assertEqual(resp.status_code, 400)
        self._assert_not_sent()

    def test_challenge_requires_rahbar(self):
        self.client.force_authenticate(self.hodim)
        resp = self.client.post(f"{BASE}/send/challenge/", {"id": str(self.report.id)}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_tampered_document_is_rejected(self):
        payload = json.loads(self._challenge())
        payload["items_hash"] = "0" * 64
        tampered = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        resp = self._send(fake_sign(tampered))
        self.assertEqual(resp.status_code, 400)
        self._assert_not_sent()

    def test_report_changed_after_challenge_is_rejected(self):
        document = self._challenge()
        self.item.value = "11"
        self.item.save()
        resp = self._send(fake_sign(document))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("o'zgartirilgan", resp.content.decode())
        self._assert_not_sent()

    def test_signature_for_other_report_is_rejected(self):
        other = Report.objects.create(organization=self.org, statement=self.stmt, deadline=self.deadline)
        document = self._challenge(other)
        resp = self._send(fake_sign(document))  # other'ning imzosi bilan self.report
        self.assertEqual(resp.status_code, 400)
        self._assert_not_sent()

    def test_certificate_tin_mismatch_is_rejected(self):
        document = self._challenge()
        resp = self._send(fake_sign(document), eimzo=FakeEimzo(tin="999999999"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("STIR", resp.content.decode())
        self._assert_not_sent()

    def test_certificate_without_tin_is_rejected(self):
        document = self._challenge()
        resp = self._send(fake_sign(document), eimzo=FakeEimzo(tin=""))
        self.assertEqual(resp.status_code, 400)
        self._assert_not_sent()

    def test_organization_without_stir_cannot_be_signed(self):
        self.report.organization = self.org_no_stir
        self.report.save(update_fields=["organization"])
        rahbar_b = User.objects.create_user(
            email="rahbar_b@example.com", password="TestPassword123!", first_name="R", last_name="B",
            role="tashkilot_rahbari", organization=self.org_no_stir,
        )
        self.client.force_authenticate(rahbar_b)
        document = self._challenge()
        resp = self._send(fake_sign(document))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("STIR", resp.content.decode())

    def test_pinfl_mismatch_with_logged_in_user_is_rejected(self):
        document = self._challenge()
        resp = self._send(fake_sign(document), eimzo=FakeEimzo(pinfl="40000000000000"))
        self.assertEqual(resp.status_code, 400)
        self._assert_not_sent()

    def test_invalid_signature_status_is_rejected(self):
        document = self._challenge()
        resp = self._send(fake_sign(document), eimzo=FakeEimzo(status=-10))
        self.assertEqual(resp.status_code, 400)
        self._assert_not_sent()

    def test_verify_unknown_signature_is_404(self):
        self.client.force_authenticate(None)
        resp = self.client.get(f"{BASE}/signatures/00000000-0000-0000-0000-000000000000/verify/")
        self.assertEqual(resp.status_code, 404)
