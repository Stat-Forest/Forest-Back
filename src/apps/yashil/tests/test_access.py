"""Rol -> URL qoidalari va modulga kirish (TZ §2.2; role_access allow-list)."""
from rest_framework.test import APITestCase

from apps.authentications.service.role_access import is_path_allowed_for_role
from apps.yashil.models import YashilMembership
from apps.yashil.tests._common import BASE, auth, make_district, make_mahalla, make_region, make_user, member


class RolePathRulesTest(APITestCase):
    def test_ym_roles_are_limited_to_module_auth_and_notifications(self):
        for role in ("ym_mahalla", "ym_union", "ym_dm", "ym_observer"):
            self.assertTrue(is_path_allowed_for_role(role, "/api/v1/yashil/orders/", "POST"), role)
            self.assertTrue(is_path_allowed_for_role(role, "/api/v1/authentications/logout/", "POST"), role)
            self.assertTrue(is_path_allowed_for_role(role, "/api/v1/general/notifications/", "GET"), role)
            self.assertFalse(is_path_allowed_for_role(role, "/api/v1/reports/", "GET"), role)
            self.assertFalse(is_path_allowed_for_role(role, "/api/v1/billing/contracts/", "GET"), role)
            self.assertFalse(is_path_allowed_for_role(role, "/api/v1/general/notifications/", "POST"), role)

    def test_support_admin_is_denied_module(self):
        self.assertFalse(is_path_allowed_for_role("support_admin", "/api/v1/yashil/me/", "GET"))

    def test_forest_organization_roles_keep_module_access(self):
        self.assertTrue(is_path_allowed_for_role("tashkilot_hodimi", "/api/v1/yashil/me/", "GET"))
        self.assertTrue(is_path_allowed_for_role("tashkilot_rahbari", "/api/v1/yashil/orders/", "POST"))


class MeEndpointTest(APITestCase):
    def setUp(self):
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)

    def test_user_without_membership_sees_empty_cabinets(self):
        user = make_user("plain")
        res = auth(self.client, user).get(f"{BASE}/me/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_member"])
        self.assertEqual(res.data["cabinets"], [])
        self.assertIsNone(res.data["active_cabinet"])

    def test_member_sees_cabinet_with_permissions(self):
        user = make_user("mah", role="ym_mahalla")
        m = member(user, YashilMembership.MemberType.MAHALLA, mahalla=self.mahalla, can_sign=False,
                   position_title="Rais", phone="+998901234567")
        res = auth(self.client, user).get(f"{BASE}/me/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_member"])
        cab = res.data["active_cabinet"]
        self.assertEqual(cab["id"], str(m.pk))
        self.assertEqual(cab["member_type"], "mahalla")
        self.assertEqual(cab["name"], "Боғистон маҳалласи")
        self.assertTrue(cab["can_prepare"])
        self.assertFalse(cab["can_sign"])
        self.assertEqual(cab["mahalla"]["district"]["code"], "1703202")

    def test_super_admin_without_membership_is_module_admin(self):
        user = make_user("root", role="super_admin", is_superuser=True, is_staff=True)
        res = auth(self.client, user).get(f"{BASE}/me/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_admin"])
        self.assertFalse(res.data["is_member"])

    def test_cabinet_header_selects_membership_and_rejects_foreign_one(self):
        user = make_user("two", role="ym_mahalla")
        other_mahalla = make_mahalla(self.district, name="Навбаҳор маҳалласи")
        m1 = member(user, YashilMembership.MemberType.MAHALLA, mahalla=self.mahalla)
        m2 = member(user, YashilMembership.MemberType.MAHALLA, mahalla=other_mahalla)
        res = auth(self.client, user, cabinet=m2).get(f"{BASE}/me/")
        self.assertEqual(res.data["active_cabinet"]["id"], str(m2.pk))
        self.assertEqual({c["id"] for c in res.data["cabinets"]}, {str(m1.pk), str(m2.pk)})
        stranger = member(make_user("x"), YashilMembership.MemberType.MAHALLA, mahalla=other_mahalla)
        res = auth(self.client, user, cabinet=stranger).get(f"{BASE}/me/")
        self.assertEqual(res.status_code, 403)

    def test_expired_membership_is_not_offered(self):
        from datetime import date
        user = make_user("old", role="ym_mahalla")
        member(user, YashilMembership.MemberType.MAHALLA, mahalla=self.mahalla,
               valid_from=date(2020, 1, 1), valid_to=date(2020, 12, 31))
        res = auth(self.client, user).get(f"{BASE}/me/")
        self.assertFalse(res.data["is_member"])

    def test_reference_endpoints_require_membership(self):
        user = make_user("nobody")
        res = auth(self.client, user).get(f"{BASE}/reference/mahallas/")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["error_code"], "not_member")
        self.assertIn("request_id", res.data)
