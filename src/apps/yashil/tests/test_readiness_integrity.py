"""Pilotga tayyorlik (TZ §19.2) va yaxlitlik tekshiruvi (TZ §17.3, Q36) buyruqlari."""
import io
import json
from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.yashil.models import CalendarDay, ServiceCapacity, StockMovement, YashilMembership
from apps.yashil.services import integrity, ledger, readiness
from apps.yashil.tests._common import (
    assign_forest, make_district, make_dm, make_forest, make_item, make_mahalla, make_region, make_union, make_user,
    member, route_union,
)

T = YashilMembership.MemberType
ON = date(2027, 1, 11)


class ReadinessTest(TestCase):
    def setUp(self):
        self.district = make_district(make_region())
        self.ready = make_mahalla(self.district, "Тайёр маҳалла")
        self.bare = make_mahalla(self.district, "Бўш маҳалла")
        self.forest = make_forest("Тайёр хўжалик")
        self.empty_forest = make_forest("Қолдиқсиз хўжалик")
        self.dm, p = make_dm("ДМ"); p.service_regions.add(self.district.region)
        assign_forest(self.ready, self.forest)
        self.unit = make_union(self.district); route_union(self.ready, self.unit)
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        self.prt = make_item("PRT", "Ҳимоя", "dm", "protection_service", "daraxt", item_type="service")
        member(make_user("m", role="ym_mahalla"), T.MAHALLA, mahalla=self.ready)
        self.f_cab = member(make_user("f", role="tashkilot_rahbari", organization=self.forest), T.SUPPLIER, organization=self.forest)
        member(make_user("u", role="ym_union"), T.UNION, union_unit=self.unit, can_sign=False)
        ledger.post_opening(ledger.default_warehouse(self.forest), self.ash, Decimal("10"), self.f_cab, doc_number="ИНВ", doc_date=date(2026, 12, 31))

    def section(self, report, key):
        return next(s for s in report["sections"] if s["key"] == key)

    def test_reports_gaps_with_samples(self):
        report = readiness.collect(on=ON)
        self.assertFalse(report["ready"])
        self.assertEqual(self.section(report, "mahalla_without_forest")["sample"], ["Бўш маҳалла"])
        self.assertEqual(self.section(report, "mahalla_without_route")["sample"], ["Бўш маҳалла"])
        self.assertEqual(self.section(report, "mahalla_without_signer")["sample"], ["Бўш маҳалла"])
        self.assertEqual(set(self.section(report, "supplier_without_signer")["sample"]), {"Қолдиқсиз хўжалик", "ДМ"})
        self.assertEqual(self.section(report, "forest_without_opening")["sample"], ["Қолдиқсиз хўжалик"])
        self.assertEqual(self.section(report, "dm_without_capacity")["sample"], ["ДМ"])
        self.assertEqual(self.section(report, "calendar_year")["count"], 1)
        self.assertEqual(self.section(report, "observers")["count"], 1)
        self.assertEqual(self.section(report, "calendar_year")["level"], "blocker")
        self.assertEqual(report["totals"], {"mahallas": 2, "suppliers": 3, "memberships": 3})
        self.assertIn("review_workdays", report["rules"])

    def test_ready_when_gaps_are_closed(self):
        self.bare.is_active = False
        self.bare.save(update_fields=["is_active"])
        for org in (self.empty_forest, self.dm):
            member(make_user(f"s{org.pk}", role="tashkilot_rahbari", organization=org), T.SUPPLIER, organization=org)
        cab = YashilMembership.objects.get(organization=self.empty_forest)
        ledger.post_opening(ledger.default_warehouse(self.empty_forest), self.ash, Decimal("5"), cab, doc_number="ИНВ", doc_date=date(2026, 12, 31))
        ServiceCapacity.objects.create(organization=self.dm, catalog_item=self.prt, period="2027-01", capacity=Decimal("10"))
        CalendarDay.objects.create(date=date(2027, 1, 1), kind="holiday", note="Янги йил")
        member(make_user("o", role="ym_observer"), T.OBSERVER, can_prepare=False, can_sign=False)
        report = readiness.collect(on=ON)
        self.assertTrue(report["ready"], [s for s in report["sections"] if s["count"]])

    def test_command_text_and_strict_exit(self):
        out = io.StringIO()
        call_command("yashil_readiness", "--date", "2027-01-11", stdout=out)
        self.assertIn("Бўш маҳалла", out.getvalue())
        with self.assertRaises(CommandError):
            call_command("yashil_readiness", "--date", "2027-01-11", "--strict", stdout=io.StringIO())
        out = io.StringIO()
        call_command("yashil_readiness", "--date", "2027-01-11", "--json", stdout=out)
        self.assertFalse(json.loads(out.getvalue())["ready"])


class IntegrityCheckTest(TestCase):
    def setUp(self):
        district = make_district(make_region())
        self.forest = make_forest()
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        assign_forest(make_mahalla(district), self.forest)
        self.cab = member(make_user("f", role="tashkilot_rahbari", organization=self.forest), T.SUPPLIER, organization=self.forest)
        ledger.post_opening(ledger.default_warehouse(self.forest), self.ash, Decimal("10"), self.cab, doc_number="ИНВ", doc_date=date(2026, 12, 31))

    def test_collect_counts_fingerprints_and_ok(self):
        report = integrity.collect()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["counts"]["stock_movements"], 1)
        self.assertEqual(report["stock_qty_by_kind"], {"opening": "10.0000"})
        before = report["fingerprints"]["stock_movements"]
        StockMovement.objects.update(qty=Decimal("11"))
        self.assertNotEqual(integrity.collect()["fingerprints"]["stock_movements"], before)

    def test_compare_reports_differences(self):
        a = integrity.collect(check_files=False)
        b = json.loads(json.dumps(a))
        b["counts"]["orders"] = 5
        b["fingerprints"]["signatures"] = "x"
        self.assertEqual(integrity.compare(a, a), [])
        diff = integrity.compare(a, b)
        self.assertIn("counts.orders: 0 → 5", diff)
        self.assertTrue(any(d.startswith("fingerprints.signatures") for d in diff))

    def test_command_json_and_compare_file(self):
        out = io.StringIO()
        call_command("yashil_integrity_check", "--json", stdout=out)
        snapshot = json.loads(out.getvalue())
        self.assertTrue(snapshot["ok"])
        path = self._tmp(json.dumps(snapshot))
        out = io.StringIO()
        call_command("yashil_integrity_check", "--compare", path, stdout=out)
        self.assertIn("Мос", out.getvalue())
        snapshot["counts"]["stock_movements"] = 2
        with self.assertRaises(CommandError):
            call_command("yashil_integrity_check", "--compare", self._tmp(json.dumps(snapshot)), stdout=io.StringIO())

    def _tmp(self, text):
        import tempfile

        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        f.write(text)
        f.close()
        self.addCleanup(lambda: __import__("os").unlink(f.name))
        return f.name
