"""
Login email bilan ham, username (eski billing logini) bilan ham ishlaydi.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

User = get_user_model()
URL = "/api/v1/authentications/login/"


class UsernameLoginTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="raximov@example.uz", password="Inspektor123!", first_name="Abdumalik", last_name="Raximov",
            role="billing_user", username="raximov_abdumalik",
        )

    def setUp(self):
        cache.clear()

    def test_login_with_username(self):
        r = self.client.post(URL, {"email": "raximov_abdumalik", "password": "Inspektor123!"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertIn("access", body.get("data", body))

    def test_login_with_username_is_case_insensitive(self):
        r = self.client.post(URL, {"email": "Raximov_Abdumalik", "password": "Inspektor123!"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_login_with_email_still_works(self):
        r = self.client.post(URL, {"email": "raximov@example.uz", "password": "Inspektor123!"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_wrong_password_with_username_is_401(self):
        r = self.client.post(URL, {"email": "raximov_abdumalik", "password": "xato"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_unknown_username_is_401(self):
        r = self.client.post(URL, {"email": "yoq_user", "password": "Inspektor123!"}, format="json")
        self.assertEqual(r.status_code, 401)
