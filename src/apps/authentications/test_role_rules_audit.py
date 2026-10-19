from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.general.models import Organization

User = get_user_model()


def make_user(name, role, **extra):
    return User.objects.create_user(
        email=f"{name}@example.com", password="TestPassword123!",
        first_name="T", last_name="U", role=role, **extra,
    )


def login(client, user):
    # Haqiqiy JWT: rol→URL qoidalari CustomJWTAuthentication ichida ishlaydi,
    # force_authenticate uni chetlab o'tadi.
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


class SupportAdminBillingDenyTest(APITestCase):
    """Audit B11: support_admin ijara billing (ijarachilar PINFL/pasporti) ni o'qimasligi kerak."""

    def test_support_admin_is_blocked_from_billing(self):
        login(self.client, make_user("support", "support_admin"))
        for url in ("/api/v1/billing/contracts/", "/api/v1/billing/renters/",
                    "/api/v1/billing/contracts/export-excel/", "/api/v1/billing/contract-files/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)


class ReportCreateRoleTest(APITestCase):
    """Audit B12: hisobot yaratish faqat tashkilot hodimi (va super_admin) uchun — has_permission darajasida."""

    def setUp(self):
        self.org = Organization.objects.create(name="Tashkilot", region="tashkent")

    def _post(self, role):
        login(self.client, make_user(role, role, organization=self.org))
        return self.client.post("/api/v1/reports/create/", {}, format="json")

    def test_rahbar_cannot_create_report(self):
        self.assertEqual(self._post("tashkilot_rahbari").status_code, 403)

    def test_billing_user_cannot_create_report(self):
        self.assertEqual(self._post("billing_user").status_code, 403)

    def test_hodim_reaches_validation(self):
        self.assertEqual(self._post("tashkilot_hodimi").status_code, 400)
