"""/admin/ va /billing-admin/ IP allowlist (ADMIN_ALLOWED_IPS)."""
from django.test import TestCase, override_settings


class AdminIPAllowlistTest(TestCase):
    def _get(self, path, ip):
        return self.client.get(path, HTTP_X_REAL_IP=ip)

    @override_settings(ADMIN_ALLOWED_IPS="203.0.113.5, 198.51.100.0/24")
    def test_admin_only_from_allowed_ips(self):
        self.assertEqual(self._get("/admin/login/", "203.0.113.5").status_code, 200)
        self.assertIn(self._get("/billing-admin/login/", "198.51.100.77").status_code, (200, 302))
        self.assertEqual(self._get("/admin/login/", "203.0.113.6").status_code, 403)
        self.assertEqual(self._get("/billing-admin/login/", "8.8.8.8").status_code, 403)
        self.assertEqual(self._get("/admin/login/", "").status_code, 403)  # X-Real-IP yo'q, REMOTE_ADDR 127.0.0.1

    @override_settings(ADMIN_ALLOWED_IPS="203.0.113.5")
    def test_api_and_public_paths_are_not_restricted(self):
        self.assertNotEqual(self._get("/api/v1/billing/public/rent-stats/", "8.8.8.8").status_code, 403)
        self.assertNotEqual(self._get("/api/v1/authentications/login/", "8.8.8.8").status_code, 403)

    @override_settings(ADMIN_ALLOWED_IPS="")
    def test_empty_setting_keeps_admin_open(self):
        self.assertEqual(self._get("/admin/login/", "8.8.8.8").status_code, 200)

    @override_settings(ADMIN_ALLOWED_IPS="not-an-ip, 203.0.113.5")
    def test_invalid_entries_are_ignored(self):
        self.assertEqual(self._get("/admin/login/", "203.0.113.5").status_code, 200)
        self.assertEqual(self._get("/admin/login/", "203.0.113.9").status_code, 403)
