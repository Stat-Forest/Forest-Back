import os
import shutil
import tempfile
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.general.models.land_document import LandDocument
from apps.general.protected_media import SALT, make_token

User = get_user_model()
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class ProtectedMediaTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmp = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.tmp, PROTECTED_MEDIA_SERVE_DIRECTLY=False)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.tmp, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.org = Organization.objects.create(name="Tashkilot A", region="tashkent")
        self.rahbariyat = User.objects.create_user(
            email="r@example.com", password="TestPassword123!", first_name="T", last_name="U", role="rahbariyat",
        )
        self.staff = User.objects.create_user(
            email="s@example.com", password="TestPassword123!", first_name="T", last_name="U",
            role="super_admin", is_staff=True,
        )
        self.doc = LandDocument.objects.create(
            name="Hujjat", date="2026-01-10", document_type="qaror", organization=self.org,
            file=SimpleUploadedFile("qaror.pdf", PDF, "application/pdf"),
        )
        self.path = self.doc.file.name  # documents/land/qaror...pdf
        self.url = f"/media/{self.path}"

    def test_unsigned_request_is_forbidden(self):
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_api_returns_signed_url_that_serves_via_accel(self):
        self.client.force_authenticate(self.rahbariyat)
        rows = self.client.get("/api/v1/general/land-documents/").json()
        rows = rows.get("results", rows)
        file_url = next(r["file_url"] for r in rows if str(r["id"]) == str(self.doc.id))
        parsed = urlparse(file_url)
        self.assertEqual(parsed.path, self.url)
        token = parse_qs(parsed.query)["t"][0]
        # xom (imzosiz) fayl yo'li javobda chiqmaydi
        self.assertNotIn("file", {k for r in rows for k in r} - {"file_url"})

        self.client.force_authenticate(None)
        resp = self.client.get(f"{parsed.path}?t={token}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["X-Accel-Redirect"], f"/protected-media/{self.path}")
        self.assertIn("attachment", resp["Content-Disposition"])

    def test_token_for_other_file_is_rejected(self):
        other = make_token("documents/land/boshqa.pdf")
        self.assertEqual(self.client.get(f"{self.url}?t={other}").status_code, 403)

    def test_expired_token_is_rejected(self):
        token = make_token(self.path)
        with override_settings(PROTECTED_MEDIA_URL_TTL=0):
            import time; time.sleep(1.1)
            self.assertEqual(self.client.get(f"{self.url}?t={token}").status_code, 403)

    def test_tampered_token_is_rejected(self):
        token = make_token(self.path)[:-3] + "abc"
        self.assertEqual(self.client.get(f"{self.url}?t={token}").status_code, 403)

    def test_staff_session_can_open_without_token(self):
        # Admin sessiyasi: faqat tegishli model ruxsati (yoki superuser) bilan (audit PM1)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        perm = Permission.objects.get(codename="view_landdocument", content_type__app_label="general")
        self.staff.user_permissions.add(perm)
        self.staff = User.objects.get(pk=self.staff.pk)  # perm keshini tozalash
        self.client.force_login(self.staff)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["X-Accel-Redirect"], f"/protected-media/{self.path}")
        # Boshqa papka (shartnoma skanlari) uchun bu ruxsat yetmaydi
        self.assertEqual(self.client.get("/media/documents/billing/contracts/2026/01/x.pdf").status_code, 403)

    def test_superuser_session_can_open_without_token(self):
        root = User.objects.create_superuser(email="root_pm@example.com", password="x", first_name="R", last_name="T")
        self.client.force_login(root)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_missing_file_with_valid_token_is_404(self):
        name = "documents/land/yoq.pdf"
        self.assertEqual(self.client.get(f"/media/{name}?t={make_token(name)}").status_code, 404)
