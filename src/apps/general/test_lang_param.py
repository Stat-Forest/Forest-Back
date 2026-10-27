"""Audit C5: `lang` parametri whitelist — ixtiyoriy matn bilan Redis'ni to'ldirib bo'lmasin."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

User = get_user_model()
JUNK = "zz" + "x" * 40


class LangParamWhitelistTest(APITestCase):
    def setUp(self):
        cache.clear()

    def test_public_lands_summary_ignores_unknown_lang(self):
        resp = self.client.get("/api/v1/general/lands/", {"lang": JUNK})
        self.assertIn(resp.status_code, (200, 400))
        self.assertIsNone(cache.get(f"land_management_summary:{JUNK}"))

    def test_notifications_ignore_unknown_lang(self):
        user = User.objects.create_user(email="n@example.com", password="TestPassword123!",
                                        first_name="T", last_name="U", role="tashkilot_hodimi")
        self.client.force_authenticate(user)
        resp = self.client.get("/api/v1/general/notifications/", {"lang": JUNK})
        self.assertIn(resp.status_code, (200, 400))
        self.assertIsNone(cache.get(f"notifications:{JUNK}"))
