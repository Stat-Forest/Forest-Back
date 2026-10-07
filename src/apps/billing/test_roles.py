"""Rol tekshiruvi: oddiy rol faqat GET, billing_user/super_admin yozadi, billing_user boshqa bo'limlarga kirmaydi."""
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.billing._tests_common import BASE, auth, contract_payload, make_reference, make_user
from apps.billing.models import Contract


class BillingRoleAccessTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        self.rahbariyat = make_user("rahbariyat", "rahbariyat")
        self.support = make_user("support", "support_admin")
        self.billing = make_user("billing", "billing_user")
        self.superadmin = make_user("admin", "super_admin", is_superuser=True, is_staff=True)

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get(f"{BASE}/contracts/").status_code, 401)

    def test_regular_role_can_read_but_not_write(self):
        client = auth(self.client, self.rahbariyat)
        for url in (f"{BASE}/contracts/", f"{BASE}/regions/", f"{BASE}/xojalik-locations/", f"{BASE}/contracts/summary/"):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 200)
        resp = client.post(f"{BASE}/contracts/", contract_payload(self.ref), format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Contract.objects.count(), 0)

    def test_support_admin_can_read_billing(self):
        self.assertEqual(auth(self.client, self.support).get(f"{BASE}/contracts/").status_code, 200)

    def test_billing_user_can_write(self):
        resp = auth(self.client, self.billing).post(f"{BASE}/contracts/", contract_payload(self.ref), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Contract.objects.count(), 1)

    def test_super_admin_can_write(self):
        resp = auth(self.client, self.superadmin).post(f"{BASE}/contracts/", contract_payload(self.ref), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_billing_user_is_blocked_from_other_modules(self):
        client = auth(self.client, self.billing)
        for url in ("/api/v1/reports/statements/", "/api/v1/reports/", "/api/v1/statistics/login-stats/",
                    "/api/v1/general/land-documents/", "/api/v1/users/verify-digital-signature/", "/api/v1/sum/employee-report/"):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 403, url)

    def test_billing_user_keeps_notifications_and_user_list(self):
        client = auth(self.client, self.billing)
        for url in ("/api/v1/general/notifications/", "/api/v1/general/announcements/", "/api/v1/reports/users/"):
            with self.subTest(url=url):
                self.assertNotEqual(client.get(url).status_code, 403, url)
