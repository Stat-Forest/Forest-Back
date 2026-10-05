from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.utils.services.tokens import create_password_reset_access_token

User = get_user_model()


class PasswordResetTokenScopeTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reset@example.com",
            password="OldPassword123!",
            first_name="Test",
            last_name="User",
            role="tashkilot_hodimi",
        )
        token = create_password_reset_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_reset_token_rejected_on_regular_endpoint(self):
        response = self.client.get("/api/v1/reports/")
        self.assertEqual(response.status_code, 401)

    def test_reset_token_rejected_on_change_password(self):
        response = self.client.post(
            "/api/v1/authentications/change-password/",
            {"old_password": "x", "new_password": "y", "confirm_password": "y"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_reset_token_accepted_on_new_password(self):
        response = self.client.post(
            "/api/v1/authentications/forgot-password/new-password/",
            {"password": "NewPassw0rd!xyz", "confirm_password": "NewPassw0rd!xyz"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassw0rd!xyz"))
