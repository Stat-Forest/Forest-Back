from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

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

    def _login(self, pinfl, tin=ORG_TIN):
        with patch("apps.e_imzo.views.eimzo_api.eri_backend_auth", return_value=_auth_ok(pinfl, tin)):
            return self.client.post(URL, {"pkcs7": "dummy"}, format="json")

    def test_known_pinfl_logs_in_as_that_user(self):
        resp = self._login(RAHBAR_PINFL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["user_id"], self.rahbar.id)

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
