"""Prod sinov hisoblari (yashil_test_accounts): mavjud mahalla va unga biriktirilgan tashkilotlarga ulanadi."""
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.yashil.models import YashilMembership
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_mahalla, make_region, make_union, route_union,
)

T = YashilMembership.MemberType
PASSWORD = "Sinov-Parol-2026!"
PINFL = "31234567890123"


def run(*args, answers=(PASSWORD, PASSWORD)):
    out = StringIO()
    with patch("apps.yashil.management.commands.yashil_test_accounts.getpass", side_effect=list(answers)):
        call_command("yashil_test_accounts", *args, stdout=out)
    return out.getvalue()


class TestAccountsCommandTest(TestCase):
    def setUp(self):
        d = make_district(make_region())
        self.mahalla = make_mahalla(d, source_code="MH-PILOT-1")
        self.bare = make_mahalla(d, "Бошқа маҳалла", source_code="MH-BARE")
        self.forest = make_forest("Пилот ўрмон хўжалиги")
        assign_forest(self.mahalla, self.forest)
        self.unit = make_union(d)
        route_union(self.mahalla, self.unit)
        self.User = get_user_model()

    def user(self, kind):
        return self.User.objects.get(email=f"ym-test-{kind}@stat-urmon.uz")

    def test_list_shows_mahallas_with_links(self):
        out = run("--list", answers=())
        self.assertIn("MH-PILOT-1", out)
        self.assertIn("Пилот ўрмон хўжалиги", out)
        self.assertIn("MH-BARE", out)

    def test_creates_four_cabinets_without_echoing_password(self):
        out = run("--mahalla", "MH-PILOT-1")
        self.assertNotIn(PASSWORD, out)
        m = self.user("mahalla")
        self.assertTrue(m.check_password(PASSWORD))
        self.assertEqual(m.role, "ym_mahalla")
        ms = YashilMembership.objects.get(user=m)
        self.assertEqual((ms.member_type, ms.mahalla_id, ms.can_prepare, ms.can_sign), (T.MAHALLA, self.mahalla.id, True, True))
        s = self.user("supplier")
        self.assertEqual(s.role, "ym_dm")  # faqat modul URL'lari; tashkilotning hisobotlariga kirmaydi
        self.assertIsNone(s.organization_id)
        self.assertEqual(YashilMembership.objects.get(user=s).organization_id, self.forest.id)
        self.assertEqual(YashilMembership.objects.get(user=self.user("union")).union_unit_id, self.unit.id)
        obs = YashilMembership.objects.get(user=self.user("observer"))
        self.assertEqual((obs.member_type, obs.can_prepare, obs.can_sign), (T.OBSERVER, False, False))

    def test_pinfl_goes_only_to_signing_cabinets(self):
        run("--mahalla", "MH-PILOT-1", "--pinfl", answers=(PASSWORD, PASSWORD, PINFL))
        self.assertEqual(self.user("mahalla").pinfl, PINFL)
        self.assertEqual(self.user("supplier").pinfl, PINFL)
        self.assertFalse(self.user("union").pinfl)

    def test_rerun_is_idempotent_and_does_not_ask_password(self):
        run("--mahalla", "MH-PILOT-1")
        run("--mahalla", "MH-PILOT-1", answers=())
        self.assertEqual(self.User.objects.filter(email__startswith="ym-test-").count(), 4)
        self.assertEqual(YashilMembership.objects.filter(user__email__startswith="ym-test-").count(), 4)

    def test_mahalla_without_links_skips_supplier_and_union(self):
        out = run("--mahalla", "MH-BARE")
        self.assertIn("ym-test-mahalla", out)
        self.assertFalse(self.User.objects.filter(email="ym-test-supplier@stat-urmon.uz").exists())
        self.assertFalse(self.User.objects.filter(email="ym-test-union@stat-urmon.uz").exists())

    def test_disable_turns_off_users_and_memberships(self):
        run("--mahalla", "MH-PILOT-1")
        run("--disable", answers=())
        self.assertFalse(self.User.objects.filter(email__startswith="ym-test-", is_active=True).exists())
        self.assertFalse(YashilMembership.objects.filter(user__email__startswith="ym-test-", is_active=True).exists())

    def test_errors(self):
        with self.assertRaises(CommandError):
            run("--mahalla", "NOPE", answers=())
        with self.assertRaises(CommandError):
            run("--mahalla", "MH-PILOT-1", answers=("123", "123"))  # zaif parol
        with self.assertRaises(CommandError):
            run("--mahalla", "MH-PILOT-1", answers=(PASSWORD, "boshqa"))
        self.assertFalse(self.User.objects.filter(email__startswith="ym-test-").exists())
