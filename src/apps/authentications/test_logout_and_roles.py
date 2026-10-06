from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TransactionTestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chat.websocket.middleware import JWTAuthMiddleware

User = get_user_model()
AUTH = "/api/v1/authentications"


def make_user(name, role):
    return User.objects.create_user(
        email=f"{name}@example.com", password="TestPassword123!",
        first_name="T", last_name="U", role=role,
    )


class LogoutRevokesTokensTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user("rahbariyat", "rahbariyat")
        refresh = RefreshToken.for_user(self.user)
        self.refresh = str(refresh)
        self.access = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_access_token_is_rejected_after_logout(self):
        self.assertEqual(self.client.get("/api/v1/reports/").status_code, 200)

        resp = self.client.post(f"{AUTH}/logout/", {"refresh": self.refresh}, format="json")
        self.assertEqual(resp.status_code, 204)

        # Muddati tugamagan bo'lsa ham access token endi ishlamaydi
        self.assertEqual(self.client.get("/api/v1/reports/").status_code, 401)
        # Refresh token blacklist'da
        self.client.credentials()
        resp = self.client.post(f"{AUTH}/token/refresh/", {"refresh": self.refresh}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_logout_without_refresh_still_revokes_access(self):
        self.assertEqual(self.client.post(f"{AUTH}/logout/", {}, format="json").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/reports/").status_code, 401)

    def test_logout_requires_auth(self):
        self.client.credentials()
        self.assertEqual(self.client.post(f"{AUTH}/logout/", {}, format="json").status_code, 401)


class RolePathAccessTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.support = make_user("support", "support_admin")
        self.rahbariyat = make_user("rahbariyat", "rahbariyat")

    def _as(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return self.client

    def test_support_admin_is_blocked_from_report_data(self):
        c = self._as(self.support)
        for url in ("/api/v1/reports/", "/api/v1/reports/plan-list/", "/api/v1/sum/employee-report/",
                    "/api/v1/report_admin_stat/stats/export/", "/api/v1/general/land-documents/",
                    "/api/v1/information-analytical/"):
            with self.subTest(url=url):
                self.assertEqual(c.get(url).status_code, 403)

    def test_support_admin_keeps_chat_and_reference_endpoints(self):
        c = self._as(self.support)
        for url in ("/api/v1/chats/conversations/list/", "/api/v1/reports/statements/",
                    "/api/v1/reports/users/", "/api/v1/statistics/login-stats/",
                    "/api/v1/general/notifications/"):
            with self.subTest(url=url):
                self.assertNotEqual(c.get(url).status_code, 403, url)

    def test_other_roles_unaffected(self):
        self.assertEqual(self._as(self.rahbariyat).get("/api/v1/reports/").status_code, 200)


class WebSocketTokenTransportTest(TransactionTestCase):
    """database_sync_to_async alohida thread'da ishlaydi — TransactionTestCase kerak."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = make_user("chat", "tashkilot_hodimi")
        self.access = str(RefreshToken.for_user(self.user).access_token)

    def _run(self, scope):
        captured = {}

        async def inner(scope, receive, send):
            captured["user"] = scope["user"]

        async_to_sync(JWTAuthMiddleware(inner))(scope, None, None)
        return captured["user"]

    def test_token_in_subprotocol_authenticates(self):
        user = self._run({"type": "websocket", "subprotocols": ["jwt", self.access], "query_string": b""})
        self.assertEqual(user, self.user)

    def test_token_in_url_is_no_longer_accepted(self):
        user = self._run({"type": "websocket", "subprotocols": [], "query_string": f"token={self.access}".encode()})
        self.assertTrue(user.is_anonymous)

    def test_revoked_token_is_rejected_on_websocket(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        self.assertEqual(self.client.post(f"{AUTH}/logout/", {}, format="json").status_code, 204)
        user = self._run({"type": "websocket", "subprotocols": ["jwt", self.access], "query_string": b""})
        self.assertTrue(user.is_anonymous)
