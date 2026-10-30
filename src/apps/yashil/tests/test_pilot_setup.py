"""Pilot boshlang'ich ma'lumotlari (yashil_pilot_setup): kalendar, katalog, bitta mahalla va mavjud xo'jalikka bog'lash."""
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.yashil.management.commands.yashil_seed_demo import CATALOG
from apps.yashil.models import (
    CalendarDay, CatalogItem, Mahalla, MahallaUnionRoute, Season, SupplierAssignment, SupplierProfile,
)
from apps.yashil.services import readiness
from apps.yashil.tests._common import BASE, auth, make_district, make_dm, make_org, make_region


def run(*args):
    out = StringIO()
    call_command("yashil_pilot_setup", *args, stdout=out)
    return out.getvalue()


class PilotSetupTest(TestCase):
    def setUp(self):
        self.district = make_district(make_region())
        self.org = make_org("Андижон ўрмон хўжалиги")

    def setup_args(self):
        return ("--district", self.district.code, "--mahalla-name", "Пилот маҳалла", "--forest", str(self.org.id))

    def test_find_lists_districts_and_organizations(self):
        out = run("--find", "Андижон")
        self.assertIn(self.district.code, out)
        self.assertIn(str(self.org.id), out)

    def test_reference_only_fills_calendar_catalog_and_seasons(self):
        run("--reference-only")
        self.assertEqual(CatalogItem.objects.count(), len(CATALOG))
        for year in (2026, 2027):
            self.assertTrue(CalendarDay.objects.filter(date__year=year, kind="holiday").exists())
        self.assertTrue(CalendarDay.objects.filter(date=date(2026, 12, 8)).exists())
        self.assertFalse(CalendarDay.objects.filter(date=date(2027, 1, 14)).exists())  # dam olish kuni emas
        self.assertTrue(Season.objects.filter(year=2026, kind="autumn").exists())
        self.assertFalse(Mahalla.objects.exists())
        gaps = {s["key"] for s in readiness.collect(on=date(2026, 10, 30))["sections"] if s["count"] and s["level"] == "blocker"}
        self.assertNotIn("calendar_year", gaps)
        self.assertNotIn("catalog", gaps)

    def test_pilot_mahalla_is_linked_to_existing_forest(self):
        out = run(*self.setup_args())
        m = Mahalla.objects.get(source_code="PILOT-001")
        self.assertEqual((m.name, m.district_id, m.region_id), ("Пилот маҳалла", self.district.id, self.district.region_id))
        self.assertEqual(SupplierProfile.objects.get(organization=self.org).supplier_type, "forest")
        self.assertEqual(SupplierAssignment.objects.get(mahalla=m).organization_id, self.org.id)
        self.assertEqual(MahallaUnionRoute.objects.get(mahalla=m).union_unit.district_id, self.district.id)
        self.assertIn("yashil_test_accounts --mahalla PILOT-001", out)

    def test_rerun_is_idempotent(self):
        run(*self.setup_args())
        run(*self.setup_args())
        self.assertEqual(Mahalla.objects.count(), 1)
        self.assertEqual(SupplierAssignment.objects.count(), 1)
        self.assertEqual(MahallaUnionRoute.objects.count(), 1)
        self.assertEqual(CatalogItem.objects.count(), len(CATALOG))

    def test_errors_change_nothing(self):
        with self.assertRaises(CommandError):
            run("--district", "0000000", "--mahalla-name", "X", "--forest", str(self.org.id))
        dm, _ = make_dm()
        with self.assertRaises(CommandError):
            run("--district", self.district.code, "--mahalla-name", "X", "--forest", str(dm.id))  # DM xo'jalik emas
        with self.assertRaises(CommandError):
            run("--district", self.district.code, "--mahalla-name", "X")
        self.assertFalse(Mahalla.objects.exists())
        self.assertFalse(CatalogItem.objects.exists())


class PilotEndToEndTest(APITestCase):
    def test_test_account_sees_forest_and_catalog(self):
        district = make_district(make_region())
        org = make_org("Андижон ўрмон хўжалиги")
        run("--district", district.code, "--mahalla-name", "Пилот маҳалла", "--forest", str(org.id))
        with patch("apps.yashil.management.commands.yashil_test_accounts.getpass", side_effect=["Sinov-Parol-2026!"] * 2):
            call_command("yashil_test_accounts", "--mahalla", "PILOT-001", stdout=StringIO())
        user = get_user_model().objects.get(email="ym-test-mahalla@stat-urmon.uz")
        cabinet = user.yashil_memberships.get()
        auth(self.client, user, cabinet)
        mahalla = Mahalla.objects.get(source_code="PILOT-001")
        res = self.client.get(f"{BASE}/suppliers/for-mahalla/{mahalla.id}/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(str(res.data["forest"]["primary"]["id"]), str(org.id))
        self.assertIsNotNone(res.data["union"])
        res = self.client.get(f"{BASE}/catalog/?supplier_type=forest")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data["results"] if isinstance(res.data, dict) else res.data)
