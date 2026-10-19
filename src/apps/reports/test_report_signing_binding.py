"""
Audit B2/B3: challenge rejimida imzolangan matn server tomonida challenge bilan
solishtiriladi (e-imzo-server javobiga ko'r-ko'rona ishonilmaydi); imzo har doim
tizimga kirgan foydalanuvchiga (PINFL / JSHSHIR) bog'lanadi.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.reports.models import ReportSignature
from apps.reports.test_report_signing import PINFL, FakeEimzo, ReportSigningTest, fake_sign

User = get_user_model()


class LenientEimzo(FakeEimzo):
    """/backend/auth istalgan imzolangan matnni qabul qiladigan (muddati o'tmagan
    boshqa challenge'ni ham) server."""

    def eri_backend_auth(self, request, pkcs7):
        cert = {"serialNumber": "abc123", "validFrom": "2026-01-01 00:00:00", "validTo": "2027-01-01 00:00:00",
                "subjectName": self._subject()}
        return True, 200, {"status": 1, "subjectCertificateInfo": cert}


class SigningBindingTest(ReportSigningTest):
    def test_challenge_mode_signed_text_is_compared_server_side(self):
        eimzo = LenientEimzo(vpn_up=False)
        ch = self._challenge_full(eimzo=eimzo)
        resp = self._send(fake_sign("boshqa-challenge-" + ch["sign_text"][:8]), eimzo=eimzo, nonce=ch["nonce"])
        self.assertEqual(resp.status_code, 400)
        self._assert_not_sent()

    def test_challenge_mode_correct_text_still_accepted(self):
        eimzo = LenientEimzo(vpn_up=False)
        ch = self._challenge_full(eimzo=eimzo)
        self.assertEqual(self._send(fake_sign(ch["sign_text"]), eimzo=eimzo, nonce=ch["nonce"]).status_code, 200)

    def test_user_without_pinfl_cannot_sign(self):
        rahbar = User.objects.create_user(
            email="rahbar_nopinfl@example.com", password="TestPassword123!", first_name="R", last_name="B",
            role="tashkilot_rahbari", organization=self.org,
        )
        self.client.force_authenticate(rahbar)
        document = self._challenge()
        resp = self._send(fake_sign(document))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("PINFL", resp.content.decode())
        self._assert_not_sent()

    def test_user_jshshr_is_accepted_as_pinfl(self):
        rahbar = User.objects.create_user(
            email="rahbar_jshshr@example.com", password="TestPassword123!", first_name="R", last_name="C",
            role="tashkilot_rahbari", organization=self.org, jshshr=PINFL,
        )
        self.client.force_authenticate(rahbar)
        document = self._challenge()
        self.assertEqual(self._send(fake_sign(document)).status_code, 200)
        self.assertEqual(ReportSignature.objects.get(report=self.report).signer_id, rahbar.id)

    def test_document_issued_to_another_user_is_rejected(self):
        other = User.objects.create_user(
            email="rahbar_other@example.com", password="TestPassword123!", first_name="R", last_name="D",
            role="tashkilot_rahbari", organization=self.org, pinfl=PINFL,
        )
        document = self._challenge()  # self.rahbar uchun berilgan
        self.client.force_authenticate(other)
        resp = self._send(fake_sign(document))
        self.assertEqual(resp.status_code, 400)
        self._assert_not_sent()
