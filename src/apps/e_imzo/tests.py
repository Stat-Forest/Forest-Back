import base64
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.authentications.service.refresh_cookie import REFRESH_COOKIE

from apps.general.models import Organization

User = get_user_model()

URL = "/api/v1/e_imzo/login/"
ORG_TIN = "300000001"
RAHBAR_PINFL = "11111111111111"
OTHER_PINFL = "22222222222222"


def _auth_ok(pinfl, tin, cn="XODIM"):
    subject = {"CN": cn, "Name": "Xodim", "SURNAME": "Xodimov", "1.2.860.3.16.1.1": tin}
    if pinfl:
        subject["1.2.860.3.16.1.2"] = pinfl
    return True, 200, {"status": 1, "subjectName": subject}


class EimzoLoginAccountBindingTest(APITestCase):
    """
    Audit A1/A2: yuridik shaxs sertifikatidagi TIN — tashkilot STIR'i, u bir
    tashkilotdagi hamma xodim uchun bir xil. U orqali boshqa foydalanuvchi
    (rahbar) akkauntiga kirib bo'lmasligi, notanish sertifikat egasi esa
    admin tasdig'isiz faol rahbar bo'lib qolmasligi kerak.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Tashkilot", region="tashkent", stir=int(ORG_TIN))
        self.rahbar = User.objects.create_user(
            email="rahbar@example.com", password="TestPassword123!",
            first_name="R", last_name="R", role="tashkilot_rahbari",
            organization=self.org, pinfl=RAHBAR_PINFL, tin=ORG_TIN,
        )

    def _challenge(self, value="9b573e40-cefd-42cc-a534-f6e78b27c2ae"):
        with patch("apps.e_imzo.views.eimzo_api.eri_challenge", return_value=(True, 200, {"challenge": value})):
            resp = self.client.get("/api/v1/e_imzo/challenge/")
        self.assertEqual(resp.status_code, 200)
        return resp.data["challenge"]

    def _login(self, pinfl, tin=ORG_TIN, challenge=None, pkcs7=None):
        # Testda "imzo" = imzolangan matnning base64'i (attached PKCS#7 ichida matn ochiq turadi)
        if challenge is None:
            challenge = self._challenge()
        body = {"pkcs7": pkcs7 or base64.b64encode(challenge.encode()).decode(), "challenge": challenge}
        with patch("apps.e_imzo.views.eimzo_api.eri_backend_auth", return_value=_auth_ok(pinfl, tin)):
            return self.client.post(URL, body, format="json")

    def test_known_pinfl_logs_in_as_that_user(self):
        resp = self._login(RAHBAR_PINFL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["user_id"], self.rahbar.id)
        # Audit A5: refresh HttpOnly cookie'da ham
        self.assertTrue(resp.cookies[REFRESH_COOKIE]["httponly"])


class EimzoLoginChallengeBindingTest(EimzoLoginAccountBindingTest):
    """Audit B1: login'da imzolanadigan matn server bergan, bir martalik challenge bo'lishi shart."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def test_client_made_challenge_is_rejected(self):
        resp = self._login(RAHBAR_PINFL, challenge="client-random-123")
        self.assertIn(resp.status_code, (400, 401, 403))
        self.assertNotIn("access", resp.data)

    def test_missing_challenge_is_rejected(self):
        ch = self._challenge()
        with patch("apps.e_imzo.views.eimzo_api.eri_backend_auth", return_value=_auth_ok(RAHBAR_PINFL, ORG_TIN)):
            resp = self.client.post(URL, {"pkcs7": base64.b64encode(ch.encode()).decode()}, format="json")
        self.assertIn(resp.status_code, (400, 401, 403))
        self.assertNotIn("access", resp.data)

    def test_pkcs7_not_containing_challenge_is_rejected(self):
        ch = self._challenge()
        resp = self._login(RAHBAR_PINFL, challenge=ch, pkcs7=base64.b64encode(b"boshqa matn").decode())
        self.assertIn(resp.status_code, (400, 401, 403))
        self.assertNotIn("access", resp.data)

    def test_challenge_is_single_use(self):
        ch = self._challenge()
        self.assertEqual(self._login(RAHBAR_PINFL, challenge=ch).status_code, 200)
        resp = self._login(RAHBAR_PINFL, challenge=ch)
        self.assertIn(resp.status_code, (400, 401, 403))

    def test_unknown_pinfl_with_same_organization_tin_does_not_get_rahbar_account(self):
        resp = self._login(OTHER_PINFL)
        self.assertNotEqual(resp.data.get("user_id"), self.rahbar.id)
        self.assertNotIn("access", resp.data)
        self.rahbar.refresh_from_db()
        self.assertEqual(self.rahbar.pinfl, RAHBAR_PINFL)

    def test_new_certificate_holder_is_created_inactive_and_not_rahbar(self):
        resp = self._login(OTHER_PINFL)
        self.assertEqual(resp.status_code, 403)
        user = User.objects.get(pinfl=OTHER_PINFL)
        self.assertFalse(user.is_active)
        self.assertNotEqual(user.role, "tashkilot_rahbari")
        self.assertEqual(user.organization_id, self.org.id)

    def test_inactive_user_stays_blocked_on_second_login(self):
        self._login(OTHER_PINFL)
        resp = self._login(OTHER_PINFL)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(User.objects.filter(pinfl=OTHER_PINFL).count(), 1)

    def test_certificate_without_pinfl_is_rejected(self):
        resp = self._login(pinfl=None)
        self.assertIn(resp.status_code, (401, 403))
        self.assertNotIn("access", resp.data)
        self.assertEqual(User.objects.count(), 1)
