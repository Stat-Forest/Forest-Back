from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.general.models.land_document import LandDocument

User = get_user_model()
URL = "/api/v1/general/land-documents/"

PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
HTML = b"<html><script>alert(1)</script></html>"


class LandDocumentScopeTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(name="Tashkilot A", region="tashkent")
        cls.org_b = Organization.objects.create(name="Tashkilot B", region="namangan")
        cls.hodim_a = cls._user("hodim_a", "tashkilot_hodimi", organization=cls.org_a)
        cls.rahbar_a = cls._user("rahbar_a", "tashkilot_rahbari", organization=cls.org_a)
        cls.hudud_a = cls._user("hudud_a", "hududiy_boshqarma")
        cls.hudud_a.region_user_orgs.add(cls.org_a)
        cls.bolim = cls._user("bolim", "bolim_admin")
        cls.rahbariyat = cls._user("rahbariyat", "rahbariyat")
        cls.support = cls._user("support", "support_admin")
        cls.doc_a = LandDocument.objects.create(name="A hujjat", date="2026-01-10", document_type="qaror", organization=cls.org_a)
        cls.doc_b = LandDocument.objects.create(name="B hujjat", date="2026-01-11", document_type="qaror", organization=cls.org_b)

    @classmethod
    def _user(cls, name, role, **extra):
        return User.objects.create_user(
            email=f"{name}@example.com", password="TestPassword123!",
            first_name="T", last_name="U", role=role, **extra,
        )

    def _names(self, user):
        self.client.force_authenticate(user)
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        rows = data.get("results", data)
        return {r["name"] for r in rows}

    def test_list_scope_by_role(self):
        self.assertEqual(self._names(self.hodim_a), {"A hujjat"})
        self.assertEqual(self._names(self.rahbar_a), {"A hujjat"})
        self.assertEqual(self._names(self.hudud_a), {"A hujjat"})
        self.assertEqual(self._names(self.bolim), {"A hujjat", "B hujjat"})
        self.assertEqual(self._names(self.rahbariyat), {"A hujjat", "B hujjat"})
        self.assertEqual(self._names(self.support), set())

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get(URL).status_code, 401)

    def _create(self, user, organization, **extra):
        self.client.force_authenticate(user)
        payload = {"name": "Yangi", "date": "01.02.2026", "document_type": "buyruq"}
        if organization is not None:
            payload["organization"] = str(organization.id)
        payload.update(extra)
        return self.client.post(URL, payload, format="multipart")

    def test_organization_user_can_only_create_for_own_org(self):
        resp = self._create(self.hodim_a, self.org_b)  # boshqa tashkilot nomidan urinadi
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(LandDocument.objects.get(id=resp.json()["id"]).organization, self.org_a)

    def test_organization_user_without_org_field(self):
        resp = self._create(self.rahbar_a, None)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(LandDocument.objects.get(id=resp.json()["id"]).organization, self.org_a)

    def test_regional_user_limited_to_region(self):
        self.assertEqual(self._create(self.hudud_a, self.org_b).status_code, 403)
        self.assertEqual(self._create(self.hudud_a, self.org_a).status_code, 201)

    def test_support_cannot_create(self):
        self.assertEqual(self._create(self.support, self.org_a).status_code, 403)

    # ---------------- fayl turi ----------------

    def test_html_disguised_as_pdf_is_rejected(self):
        resp = self._create(self.bolim, self.org_a, file=SimpleUploadedFile("x.pdf", HTML, "application/pdf"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("mos kelmaydi", resp.content.decode())

    def test_html_extension_is_rejected(self):
        resp = self._create(self.bolim, self.org_a, file=SimpleUploadedFile("x.html", HTML, "text/html"))
        self.assertEqual(resp.status_code, 400)

    def test_real_pdf_is_accepted(self):
        resp = self._create(self.bolim, self.org_a, file=SimpleUploadedFile("x.pdf", PDF, "application/pdf"))
        self.assertEqual(resp.status_code, 201, resp.content)


class FakeHttp:
    def __init__(self, status_code, data):
        self.status_code, self._data = status_code, data
        import json
        self.text = json.dumps(data) if isinstance(data, dict) else str(data)

    def json(self):
        return self._data


class CheckEimzoVpnCommandTest(APITestCase):
    def _run(self, ping, info):
        def fake_get(url, **kw):
            return ping if url.endswith("/ping") else info
        out, err = StringIO(), StringIO()
        with patch("apps.e_imzo.management.commands.check_eimzo_vpn.requests.get", side_effect=fake_get):
            try:
                call_command("check_eimzo_vpn", stdout=out, stderr=err)
                code = 0
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue() + err.getvalue()

    def test_ok(self):
        info = {"vpnKeyInfo": {"validTo": "2099.01.01 00:00:00", "subjectInfo": {"CN": "stat-urmon.uz"}}}
        code, text = self._run(FakeHttp(200, {"vpnKeyInfo": {}}), FakeHttp(200, info))
        self.assertEqual(code, 0, text)
        self.assertIn("OK", text)

    def test_expired_key_and_vpn_down(self):
        info = {"vpnKeyInfo": {"validTo": "2026.01.09 16:35:00", "subjectInfo": {"CN": "stat-urmon.uz"}}}
        code, text = self._run(FakeHttp(200, "UNAVAILABLE: Network closed"), FakeHttp(200, info))
        self.assertEqual(code, 1)
        self.assertIn("TUGAGAN", text)
        self.assertIn("VPN ulanmadi", text)
