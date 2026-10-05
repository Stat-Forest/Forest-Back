from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class ApiDocsAccessTest(APITestCase):
    """Swagger/Redoc/schema faqat admin (is_staff) uchun ochiq."""

    def _user(self, email, is_staff=False):
        return User.objects.create_user(
            email=email,
            password="TestPassword123!",
            first_name="Test",
            last_name="User",
            role="tashkilot_hodimi",
            is_staff=is_staff,
        )

    def test_anonymous_docs_pages_redirect_to_admin_login(self):
        for url in ("/", "/api/redoc/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn("/admin/login/", response["Location"])

    def test_anonymous_schema_forbidden(self):
        response = self.client.get("/api/schema/")
        self.assertIn(response.status_code, (401, 403))

    def test_regular_user_jwt_cannot_read_schema(self):
        user = self._user("user@example.com")
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 403)

    def test_regular_user_session_redirected(self):
        self.client.force_login(self._user("user2@example.com"))
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)

    def test_staff_session_can_open_docs_and_schema(self):
        self.client.force_login(self._user("staff@example.com", is_staff=True))
        for url in ("/", "/api/redoc/", "/api/schema/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
