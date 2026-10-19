"""Audit C15: ichki e-imzo-server javob matni (stack trace, ichki URL) mijozga qaytarilmaydi."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class _Resp:
    def __init__(self, text, status_code=500):
        self.text, self.status_code = text, status_code

    def json(self):
        raise ValueError("not json")


INTERNAL = "java.lang.NullPointerException at uz.yt.eimzo.Server:42 http://e_imzo_server:8080/internal"


class EimzoErrorMessageTest(APITestCase):
    def setUp(self):
        self.client.force_authenticate(User.objects.create_user(
            email="u@example.com", password="TestPassword123!", first_name="T", last_name="U", role="tashkilot_rahbari"))

    def test_save_pkcs7_hides_internal_error_text(self):
        with patch("apps.e_imzo.views.eimzo_api.timestamp_pkcs7", return_value=(500, _Resp(INTERNAL))):
            resp = self.client.post("/api/v1/e_imzo/save-pkcs7/", {"pkcs7b64": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("NullPointer", resp.content.decode())
        self.assertNotIn("e_imzo_server", resp.content.decode())

    def test_verify_pkcs7_hides_internal_error_text(self):
        with patch("apps.e_imzo.views.eimzo_api.eimzo_verify", return_value=(500, _Resp(INTERNAL))):
            resp = self.client.post("/api/v1/e_imzo/verify-pkcs7/", {"pkcs7b64": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("NullPointer", resp.content.decode())
