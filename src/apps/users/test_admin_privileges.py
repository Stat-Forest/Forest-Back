from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase, RequestFactory

from apps.base.admin import admin_site
from apps.users.admin import CustomUserAdmin

User = get_user_model()


def make_user(name, **extra):
    return User.objects.create_user(
        email=f"{name}@example.com", password="TestPassword123!",
        first_name="T", last_name="U", **extra,
    )


class UsersAdminPrivilegeTest(TestCase):
    """
    Audit A9: superuser bo'lmagan staff xodim admin orqali o'zini (yoki boshqani)
    superuser/super_admin qila olmasligi, parol hash'i formada ko'rinmasligi kerak.
    """

    def setUp(self):
        self.staff = make_user("staff", role="bolim_admin", is_staff=True)
        self.staff.user_permissions.add(
            *Permission.objects.filter(codename__in=["view_customuser", "change_customuser", "add_customuser"])
        )
        self.root = make_user("root", role="super_admin", is_staff=True, is_superuser=True)
        self.victim = make_user("victim", role="tashkilot_hodimi")
        self.change_url = f"/admin/users/customuser/{self.victim.pk}/change/"
        self.ma = CustomUserAdmin(User, admin_site)

    def test_staff_change_page_hides_privilege_fields_and_password_hash(self):
        self.client.force_login(self.staff)
        resp = self.client.get(self.change_url)
        self.assertEqual(resp.status_code, 200)
        for name in ("is_superuser", "is_staff", "user_permissions", "groups"):
            self.assertNotContains(resp, f'name="{name}"')
        self.assertNotContains(resp, 'name="password"')
        self.assertNotContains(resp, "pbkdf2_sha256$")

    def test_superuser_change_page_shows_privilege_fields(self):
        self.client.force_login(self.root)
        resp = self.client.get(self.change_url)
        self.assertContains(resp, 'name="is_superuser"')
        self.assertNotContains(resp, "pbkdf2_sha256$")

    def test_add_page_asks_for_new_password_twice(self):
        self.client.force_login(self.root)
        resp = self.client.get("/admin/users/customuser/add/")
        self.assertContains(resp, 'name="password1"')
        self.assertContains(resp, 'name="password2"')

    def test_staff_cannot_save_super_admin_role(self):
        request = RequestFactory().post(self.change_url)
        request.user = self.staff
        self.victim.role = "super_admin"
        form = SimpleNamespace(cleaned_data={}, changed_data=["role"])
        with self.assertRaises(PermissionDenied):
            self.ma.save_model(request, self.victim, form, change=True)
        self.victim.refresh_from_db()
        self.assertEqual(self.victim.role, "tashkilot_hodimi")
