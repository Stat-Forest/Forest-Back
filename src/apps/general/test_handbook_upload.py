from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.general.models.handbook import Handbook

User = get_user_model()
URL = "/api/v1/general/handbooks/"
PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def make_user(name, role):
    return User.objects.create_user(
        email=f"{name}@example.com", password="TestPassword123!",
        first_name="T", last_name="U", role=role,
    )


class HandbookUploadPermissionTest(APITestCase):
    """Audit B5: ma'lumotnoma (handbook) yuklash har qanday xodimga emas, faqat super_admin/rahbariyatga."""

    def _post(self, user):
        self.client.force_authenticate(user)
        return self.client.post(URL, {"name": "Qo'llanma", "file": SimpleUploadedFile("q.pdf", PDF, "application/pdf")},
                                format="multipart")

    def test_hodim_cannot_upload_handbook(self):
        resp = self._post(make_user("hodim", "tashkilot_hodimi"))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Handbook.objects.count(), 0)

    def test_super_admin_can_upload_handbook(self):
        self.assertEqual(self._post(make_user("admin", "super_admin")).status_code, 201)

    def test_hodim_can_still_read_handbooks(self):
        self.client.force_authenticate(make_user("hodim2", "tashkilot_hodimi"))
        self.assertEqual(self.client.get(URL).status_code, 200)
