"""Audit C14: backup fayllari va legacy_billing/ ochiq /media/ ostida bo'lmasin."""
from django.test import TestCase

from apps.general.models.back_up import backup_upload_path
from apps.general.protected_media import protected_prefixes


class ProtectedPrefixesTest(TestCase):
    def test_backup_files_go_under_protected_documents_prefix(self):
        self.assertTrue(backup_upload_path(None, "db.zip").startswith("documents/"))

    def test_legacy_billing_and_backups_are_protected(self):
        prefixes = protected_prefixes()
        self.assertIn("legacy_billing/", prefixes)
        self.assertIn("documents/", prefixes)

    def test_legacy_billing_url_is_routed_through_protected_view(self):
        # Token'siz 403 (ochiq static emas, 404 ham emas)
        self.assertEqual(self.client.get("/media/legacy_billing/contracts.json").status_code, 403)
