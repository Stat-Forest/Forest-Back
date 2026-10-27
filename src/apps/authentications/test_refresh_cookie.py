"""
Audit A5: refresh token JS o'qiy olmaydigan HttpOnly cookie'da (frontend uni
localStorage/cookie'ga yozmaydi). /token/refresh/ va /logout/ cookie'dan o'qiydi.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.authentications.service.refresh_cookie import REFRESH_COOKIE

User = get_user_model()
AUTH = "/api/v1/authentications"


class RefreshCookieTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="cookie@example.com", password="TestPassword123!",
            first_name="T", last_name="U", role="tashkilot_hodimi",
        )

    def _login(self):
        resp = self.client.post(f"{AUTH}/login/", {"email": "cookie@example.com", "password": "TestPassword123!"},
                                format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp

    def test_login_sets_httponly_refresh_cookie(self):
        resp = self._login()
        cookie = resp.cookies[REFRESH_COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["path"], "/api/v1/authentications/")
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertTrue(cookie.value)
        # refresh faqat cookie'da — JSON tanasida yo'q
        self.assertNotIn("refresh", resp.data)

    def test_refresh_with_cookie_only_rotates_cookie_and_hides_refresh(self):
        old = self._login().cookies[REFRESH_COOKIE].value
        self.client.credentials()
        resp = self.client.post(f"{AUTH}/token/refresh/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("access", resp.data)
        self.assertNotIn("refresh", resp.data)
        new = resp.cookies[REFRESH_COOKIE].value
        self.assertTrue(new and new != old)
        # Eski (blacklist'dagi) cookie bilan qayta refresh bo'lmaydi
        self.client.cookies[REFRESH_COOKIE] = old
        self.assertEqual(self.client.post(f"{AUTH}/token/refresh/", {}, format="json").status_code, 401)

    def test_refresh_with_body_still_works(self):
        refresh = self._login().cookies[REFRESH_COOKIE].value
        self.client.cookies.clear()
        resp = self.client.post(f"{AUTH}/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("refresh", resp.data)

    def test_logout_with_cookie_blacklists_and_clears_cookie(self):
        login = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        resp = self.client.post(f"{AUTH}/logout/", {}, format="json")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.cookies[REFRESH_COOKIE]["max-age"], 0)
        self.client.credentials()
        self.client.cookies[REFRESH_COOKIE] = login.cookies[REFRESH_COOKIE].value
        self.assertEqual(self.client.post(f"{AUTH}/token/refresh/", {}, format="json").status_code, 401)
