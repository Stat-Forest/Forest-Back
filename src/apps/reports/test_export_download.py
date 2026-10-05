import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.logs.models import HistoryActionJournal

User = get_user_model()

URL = "/api/v1/reports/export-excel/download/"


class ReportExcelDownloadTest(APITestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.export_dir = os.path.join(self.tmp.name, "exports")
        os.makedirs(self.export_dir)
        self.override = override_settings(EXPORT_ROOT=self.export_dir)
        self.override.enable()

        # Export papkasidan tashqaridagi "maxfiy" fayl
        self.secret_path = os.path.join(self.tmp.name, "secret.xlsx")
        with open(self.secret_path, "wb") as f:
            f.write(b"SECRET")

        self.filename = "O'rmon_barpo_2026-10-03_10-00.xlsx"
        with open(os.path.join(self.export_dir, self.filename), "wb") as f:
            f.write(b"EXPORT")

        self.owner = self._user("owner@example.com")
        self.other = self._user("other@example.com")
        HistoryActionJournal.objects.create(
            user=self.owner,
            action="change",
            model_name="ReportExport",
            object_repr=self.filename,
        )

    def tearDown(self):
        self.override.disable()
        self.tmp.cleanup()

    def _user(self, email):
        return User.objects.create_user(
            email=email,
            password="TestPassword123!",
            first_name="Test",
            last_name="User",
            role="tashkilot_hodimi",
        )

    def _get(self, user, filename):
        self.client.force_authenticate(user)
        return self.client.get(URL, {"filename": filename})

    def test_owner_can_download_own_export(self):
        response = self._get(self.owner, self.filename)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"EXPORT")

    def test_other_user_cannot_download_foreign_export(self):
        response = self._get(self.other, self.filename)
        self.assertEqual(response.status_code, 404)

    def test_relative_path_traversal_is_rejected(self):
        response = self._get(self.owner, "../secret.xlsx")
        self.assertEqual(response.status_code, 404)

    def test_absolute_path_is_rejected(self):
        response = self._get(self.owner, self.secret_path)
        self.assertEqual(response.status_code, 404)

    def test_non_xlsx_file_is_rejected(self):
        response = self._get(self.owner, "../../.env")
        self.assertEqual(response.status_code, 404)

    def test_anonymous_is_rejected(self):
        response = self.client.get(URL, {"filename": self.filename})
        self.assertEqual(response.status_code, 401)
