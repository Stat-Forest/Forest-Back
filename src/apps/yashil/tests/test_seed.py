"""Sintetik namuna ma'lumotlari (faqat lokal/test muhit uchun) — idempotent."""
import io

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.yashil.models import CatalogItem, Mahalla, SupplierAssignment, SupplierProfile, UnionUnit, YashilMembership


class SeedDemoTest(TestCase):
    def run_seed(self):
        out = io.StringIO()
        call_command("yashil_seed_demo", stdout=out)
        return out.getvalue()

    @override_settings(DEBUG=True)
    def test_seed_creates_reference_and_demo_users_idempotently(self):
        self.run_seed()
        counts = (
            Mahalla.objects.count(), SupplierProfile.objects.count(), UnionUnit.objects.count(),
            CatalogItem.objects.count(), YashilMembership.objects.count(), SupplierAssignment.objects.count(),
        )
        self.assertGreaterEqual(counts[0], 4)
        self.assertEqual(SupplierProfile.objects.filter(supplier_type="forest").count(), 2)
        self.assertGreaterEqual(SupplierProfile.objects.filter(supplier_type="dm").count(), 2)
        self.assertTrue(CatalogItem.objects.filter(supplier_type="forest", category="seedling").exists())
        self.assertTrue(CatalogItem.objects.filter(item_type="service").exists())
        User = get_user_model()
        for email, mt in (("mahalla@test.uz", "mahalla"), ("uyushma@test.uz", "union"), ("dm@test.uz", "supplier"),
                          ("kuzatuvchi@test.uz", "observer"), ("xojalik@test.uz", "supplier")):
            user = User.objects.get(email=email)
            self.assertTrue(user.check_password("Test12345!"))
            self.assertTrue(YashilMembership.objects.filter(user=user, member_type=mt).exists(), email)
        self.run_seed()
        self.assertEqual(counts, (
            Mahalla.objects.count(), SupplierProfile.objects.count(), UnionUnit.objects.count(),
            CatalogItem.objects.count(), YashilMembership.objects.count(), SupplierAssignment.objects.count(),
        ))

    @override_settings(DEBUG=True)
    def test_seed_with_orders_creates_five_states_once(self):
        from apps.yashil.models import Order

        call_command("yashil_seed_demo", "--with-orders", stdout=io.StringIO())
        call_command("yashil_seed_demo", "--with-orders", stdout=io.StringIO())
        self.assertEqual(Order.objects.count(), 5)
        self.assertEqual(set(Order.objects.values_list("state", flat=True)),
                         {"draft", "union_new", "supplier_new", "returned", "execution"})
        self.assertEqual(Order.objects.exclude(number__isnull=True).count(), 4)

    @override_settings(DEBUG=False)
    def test_seed_refuses_outside_debug_without_force(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.run_seed()
