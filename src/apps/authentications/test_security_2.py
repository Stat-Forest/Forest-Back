"""
Chuqur xavfsizlik auditi (2026-10-27) — autentifikatsiya: parolni tiklash tokeni
inactivity'ga bog'liq emas (F2), bekor qilingan token last_activity'ni
yangilamaydi (F13), login dublikatida 500 yo'q (L2/F8), user throttle sozlangan (F4).
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()
AUTH = "/api/v1/authentications"


class Security2AuthTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="sec2@example.com", password="TestPassword123!",
            first_name="T", last_name="U", role="tashkilot_hodimi",
        )

    def test_password_reset_token_works_after_long_inactivity(self):
        # Foydalanuvchi 1 soat oldin faol bo'lgan — pwd_reset tokeni 401 bermasligi kerak
        self.user.last_activity = timezone.now() - timedelta(hours=1)
        self.user.save(update_fields=["last_activity"])
        token = AccessToken.for_user(self.user)
        token["pwd_reset"] = True
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.post(f"{AUTH}/forgot-password/new-password/", {}, format="json")
        self.assertNotEqual(resp.status_code, 401, resp.content)

    def test_password_reset_token_is_rejected_on_other_endpoints(self):
        token = AccessToken.for_user(self.user)
        token["pwd_reset"] = True
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/v1/reports/deadlines/").status_code, 401)

    def test_revoked_token_does_not_touch_last_activity(self):
        login = self.client.post(f"{AUTH}/login/", {"email": "sec2@example.com", "password": "TestPassword123!"},
                                 format="json")
        access = login.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(self.client.post(f"{AUTH}/logout/").status_code, 204)
        User.objects.filter(pk=self.user.pk).update(last_activity=None)
        resp = self.client.get("/api/v1/reports/deadlines/")
        self.assertEqual(resp.status_code, 401)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.last_activity)

    def test_duplicate_username_login_does_not_crash(self):
        User.objects.create_user(email="i1@example.com", password="TestPassword123!", first_name="T", last_name="U",
                                 role="billing_user", username="Inspektor")
        User.objects.create_user(email="i2@example.com", password="TestPassword123!", first_name="T", last_name="U",
                                 role="billing_user", username="inspektor")
        self.assertIsNone(authenticate(request=None, username="INSPEKTOR", password="TestPassword123!"))
        resp = self.client.post(f"{AUTH}/login/", {"email": "INSPEKTOR", "password": "TestPassword123!"}, format="json")
        self.assertIn(resp.status_code, (400, 401))

    def test_user_throttle_is_configured(self):
        self.assertIn("rest_framework.throttling.UserRateThrottle", settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"])
        self.assertIn("user", settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])
        self.assertIn("export", settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])
