"""Yuklama sinovi seed'i (Q35): kichik hajmda yaratish, yaxlitlik, tokenlar, tozalash, himoya."""
import io
import json
import os
import tempfile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.yashil.models import Acceptance, Act, Mahalla, Order, OrderState, StockMovement, YashilMembership
from apps.yashil.services import integrity
from apps.yashil.tests._common import make_district, make_item, make_region


class SeedLoadTest(TestCase):
    def setUp(self):
        region = make_region()
        make_district(region, "1703202", "Андижон тумани")
        make_district(region, "1703203", "Асака тумани")
        make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        make_item("MUL", "Мульча", "forest", "mulch", "kg")
        make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        make_item("PRT", "Ҳимоя", "dm", "protection_service", "daraxt", item_type="service")

    def seed(self, *extra):
        call_command("yashil_seed_load", "--orders", "300", "--mahallas", "20", "--forests", "3", "--dms", "2",
                     "--users", "10", "--password", "LoadPass-12345", "--batch", "120", *extra, stdout=io.StringIO())

    def test_refuses_outside_test_environment(self):
        with self.assertRaises(CommandError):
            self.seed()

    @override_settings(DEBUG=True)
    def test_seed_is_consistent_and_purge_removes_only_synthetic_rows(self):
        tokens = os.path.join(tempfile.mkdtemp(), "t.json")
        self.seed("--tokens-out", tokens)
        orders = Order.objects.filter(number__startswith="LD-")
        self.assertEqual(orders.count(), 300)
        self.assertEqual(Mahalla.objects.filter(source_code__startswith="LOAD-").count(), 20)
        self.assertGreater(orders.filter(state=OrderState.EXECUTION).count(), 0)
        accepted = orders.filter(state__in=["execution", "partial", "closed"])
        self.assertEqual(Acceptance.objects.count(), accepted.count())
        self.assertEqual(Act.objects.count(), orders.filter(state__in=["partial", "closed"]).count())
        self.assertTrue(StockMovement.objects.filter(kind="allocate").exists())
        report = integrity.collect(check_files=False)
        self.assertEqual((report["tampered_count"], report["ledger_error_count"]), (0, 0), report["ledger_errors"])
        rows = json.load(open(tokens, encoding="utf-8"))
        self.assertEqual(len(rows), 10)
        self.assertEqual({r["kind"] for r in rows}, {"mahalla", "union", "forest", "dm", "observer"})
        self.assertTrue(YashilMembership.objects.filter(pk=rows[0]["cabinet"]).exists())
        with self.assertRaises(CommandError):
            self.seed()  # takror — avval purge
        call_command("yashil_seed_load", "--purge", stdout=io.StringIO())
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Mahalla.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)
        self.assertEqual(YashilMembership.objects.count(), 0)
