"""Audit C1/C2/C3: login timing, email bo'yicha bloklash, parol o'zgarganda tokenlar."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentications.backends import EmailBackend
from apps.utils.services.tokens import create_password_reset_access_token

User = get_user_model()
AUTH = "/api/v1/authentications"
PWD = "TestPassword123!"


def make_user(email="user@example.com"):
    return User.objects.create_user(email=email, password=PWD, first_name="T", last_name="U", role="tashkilot_hodimi")


class LoginTimingTest(APITestCase):
    def test_unknown_user_still_runs_password_hasher(self):
        # C1: foydalanuvchi topilmasa ham hash hisoblanadi — vaqt bo'yicha email aniqlab bo'lmasin
        with patch.object(User, "set_password") as dummy:
            self.assertIsNone(EmailBackend().authenticate(None, username="nobody@example.com", password="x"))
        dummy.assert_called_once()


class ResetEmailAsyncTest(APITestCase):
    def test_reset_code_email_is_sent_through_celery_task(self):
        make_user("reset@example.com")
        cache.clear()
        with patch("apps.authentications.tasks.send_reset_password_email_task.delay") as delay:
            resp = self.client.post(f"{AUTH}/forgot-password/send-code/", {"email": "reset@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        delay.assert_called_once()
        self.assertEqual(len(mail.outbox), 0)  # so'rov ichida sinxron yuborilmaydi


class PerEmailLockoutTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()

    def _login(self, password, ip):
        return self.client.post(f"{AUTH}/login/", {"email": self.user.email, "password": password},
                                format="json", HTTP_X_REAL_IP=ip)

    @patch("apps.authentications.service.throttles.LoginEmailThrottle.allow_request", return_value=True)
    @patch("apps.authentications.service.throttles.LoginIPThrottle.allow_request", return_value=True)
    def test_rotating_ips_cannot_exceed_per_email_failure_cap(self, *_):
        # C2: DRF throttle'siz ham, har IP'dan 4 tadan (IP bloki 5 da) — jami 10 xato
        for i, n in ((0, 4), (1, 4), (2, 2)):
            for _ in range(n):
                self.assertEqual(self._login("wrong", f"10.0.0.{i}").status_code, 401)
        # Yangi IP'dan to'g'ri parol bilan ham — email vaqtincha bloklangan
        self.assertEqual(self._login(PWD, "10.0.0.99").status_code, 429)


class PasswordChangeRevokesTokensTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()

    def test_other_access_tokens_die_after_password_change(self):
        # C3: boshqa qurilmadagi (oldin berilgan) access token
        other = str(RefreshToken.for_user(self.user).access_token)
        current = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {current}")
        resp = self.client.post(f"{AUTH}/change-password/",
                                {"old_password": PWD, "new_password": "NewPassw0rd!xyz", "confirm_password": "NewPassw0rd!xyz"},
                                format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {other}")
        self.assertEqual(self.client.get("/api/v1/reports/").status_code, 401)

    def test_reset_token_is_single_use(self):
        token = create_password_reset_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        body = {"password": "NewPassw0rd!xyz", "confirm_password": "NewPassw0rd!xyz"}
        self.assertEqual(self.client.post(f"{AUTH}/forgot-password/new-password/", body, format="json").status_code, 200)
        body = {"password": "Another0ne!xyz", "confirm_password": "Another0ne!xyz"}
        self.assertEqual(self.client.post(f"{AUTH}/forgot-password/new-password/", body, format="json").status_code, 401)
