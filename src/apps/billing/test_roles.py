"""
Rol tekshiruvi: oddiy rol faqat GET; billing_user (o'z xo'jaliklari), billing_super,
super_admin yozadi; billing rollari stat'da faqat kadastr bo'limini (read-only) ko'radi.
"""
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.authentications.service.role_access import is_path_allowed_for_role
from apps.billing._tests_common import BASE, auth, contract_payload, make_billing_user, make_reference, make_user
from apps.billing.models import Contract


class BillingRoleAccessTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        self.rahbariyat = make_user("rahbariyat", "rahbariyat")
        self.support = make_user("support", "support_admin")
        self.billing = make_billing_user("billing", self.ref.xojalik)
        self.billing_super = make_user("bsuper", "billing_super")
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

    def test_support_admin_cannot_read_billing(self):
        # Audit B11: ijarachilar PINFL/pasporti support_admin uchun yopiq
        self.assertEqual(auth(self.client, self.support).get(f"{BASE}/contracts/").status_code, 403)

    def test_billing_user_can_write(self):
        resp = auth(self.client, self.billing).post(f"{BASE}/contracts/", contract_payload(self.ref), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Contract.objects.count(), 1)

    def test_billing_super_can_write(self):
        resp = auth(self.client, self.billing_super).post(f"{BASE}/contracts/", contract_payload(self.ref), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_super_admin_can_write(self):
        resp = auth(self.client, self.superadmin).post(f"{BASE}/contracts/", contract_payload(self.ref), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_billing_roles_are_blocked_from_other_modules(self):
        for user in (self.billing, self.billing_super):
            client = auth(self.client_class(), user)
            for url in ("/api/v1/reports/plan-list/", "/api/v1/statistics/login-stats/", "/api/v1/general/handbooks/",
                        "/api/v1/sum/employee-report/",
                        "/api/v1/information-analytical/", "/api/v1/reports/dashboard/"):
                with self.subTest(role=user.role, url=url):
                    self.assertEqual(client.get(url).status_code, 403, url)

    def test_billing_roles_keep_kadastr_read_endpoints(self):
        for user in (self.billing, self.billing_super):
            client = auth(self.client_class(), user)
            for url in ("/api/v1/reports/statements/", "/api/v1/reports/", "/api/v1/reports/deadlines/",
                        "/api/v1/reports/individual/", "/api/v1/general/land-documents/",
                        "/api/v1/general/notifications/", "/api/v1/general/announcements/", "/api/v1/reports/users/"):
                with self.subTest(role=user.role, url=url):
                    self.assertNotEqual(client.get(url).status_code, 403, url)

    def test_billing_roles_cannot_write_outside_billing(self):
        client = auth(self.client, self.billing_super)
        for url in ("/api/v1/reports/create/", "/api/v1/general/land-documents/", "/api/v1/reports/send/"):
            with self.subTest(url=url):
                self.assertEqual(client.post(url, {}, format="json").status_code, 403, url)


class RoleAccessRulesUnitTest(APITestCase):
    def test_method_aware_allowlist(self):
        for role in ("billing_user", "billing_super"):
            with self.subTest(role=role):
                self.assertTrue(is_path_allowed_for_role(role, "/api/v1/reports/statements/", "GET"))
                self.assertTrue(is_path_allowed_for_role(role, "/api/v1/statistics/monitor-forest-uzlashtirish/", "GET"))
                self.assertTrue(is_path_allowed_for_role(role, "/api/v1/reports/", "GET"))
                self.assertFalse(is_path_allowed_for_role(role, "/api/v1/reports/plans/", "GET"))
                self.assertFalse(is_path_allowed_for_role(role, "/api/v1/reports/plan-list/", "GET"))
                self.assertFalse(is_path_allowed_for_role(role, "/api/v1/reports/create/", "POST"))
                self.assertFalse(is_path_allowed_for_role(role, "/api/v1/reports/statements/", "POST"))
                self.assertFalse(is_path_allowed_for_role(role, "/api/v1/general/land-documents/", "POST"))
                self.assertTrue(is_path_allowed_for_role(role, "/api/v1/billing/contracts/", "POST"))
                self.assertTrue(is_path_allowed_for_role(role, "/api/v1/billing/contract-files/x/", "DELETE"))
                self.assertTrue(is_path_allowed_for_role(role, "/api/v1/reports/export-excel/", "POST"))
                self.assertTrue(is_path_allowed_for_role(role, "/api/v1/chats/conversations/", "POST"))
                self.assertTrue(is_path_allowed_for_role(role, "/api/v1/authentications/logout/", "POST"))

    def test_support_admin_rules_unchanged_and_default_method(self):
        self.assertFalse(is_path_allowed_for_role("support_admin", "/api/v1/reports/"))
        self.assertTrue(is_path_allowed_for_role("support_admin", "/api/v1/reports/statements/"))
        self.assertFalse(is_path_allowed_for_role("support_admin", "/api/v1/billing/contracts/"))
        self.assertTrue(is_path_allowed_for_role("rahbariyat", "/api/v1/reports/create/", "POST"))
