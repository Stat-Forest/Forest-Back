"""Muhitga bog'liq modul sozlamalari .env orqali beriladi (sozlamalar pasporti, TZ §24)."""
from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.yashil.services.documents import verify_url


class YashilEnvSettingsTest(SimpleTestCase):
    def test_settings_exist_with_safe_defaults(self):
        self.assertTrue(settings.YASHIL_PUBLIC_BASE_URL.startswith("https://"))
        self.assertIsInstance(settings.EIMZO_REQUIRE_TIMESTAMP, bool)

    @override_settings(YASHIL_PUBLIC_BASE_URL="https://test.example.uz/")
    def test_qr_link_follows_environment(self):
        self.assertTrue(verify_url("abc").startswith("https://test.example.uz/"))
