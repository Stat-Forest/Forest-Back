"""Qator va buyurtma validatsiyasi: birlik aniqligi, takror, meyorlar, xarita (TZ §4, §5.3; javoblar В2–В4, Г4)."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.yashil.models import NormRule, YashilMembership
from apps.yashil.services.norms import OrderValidationError, validate_lines, validate_for_submit
from apps.yashil.tests._common import (
    assign_forest, make_district, make_dm, make_forest, make_item, make_mahalla, make_region, make_user, member,
)
from apps.yashil.models import Order, OrderLine


class LineValidationTest(TestCase):
    def setUp(self):
        self.forest = make_forest()
        self.dm, _ = make_dm()
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        self.mul = make_item("MUL", "Мульча", "forest", "mulch", "kg")
        self.bio = make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        self.prot = make_item("PRT", "Ҳимоя", "dm", "protection_service", "daraxt", item_type="service")
        self.old = make_item("OLD", "Эски", "forest", "seedling", "tup", is_active=False)
        NormRule.objects.create(code="fertilizer_per_tup_kg", description="Биогумус 5 кг/туп", applies_to_category="fertilizer",
                                params={"max_per_tup": 5}, effective_from=date(2026, 1, 1))
        NormRule.objects.create(code="mulch_per_tup_kg", description="Мульча 4 кг/туп", applies_to_category="mulch",
                                params={"max_per_tup": 4}, effective_from=date(2026, 1, 1))

    def err(self, lines, supplier_type="forest", **ctx):
        with self.assertRaises(OrderValidationError) as cm:
            validate_lines(lines, supplier_type=supplier_type, **ctx)
        return cm.exception

    def test_at_least_one_line(self):
        self.assertEqual(self.err([]).field, "lines")

    def test_quantity_precision_and_sign(self):
        e = self.err([{"catalog_item": self.ash, "qty": Decimal("10.5")}])
        self.assertEqual((e.field, e.index), ("lines", 0))
        self.err([{"catalog_item": self.ash, "qty": Decimal("0")}])
        validate_lines([{"catalog_item": self.ash, "qty": Decimal("10")}], supplier_type="forest")

    def test_item_must_match_supplier_type_and_be_active(self):
        self.assertEqual(self.err([{"catalog_item": self.bio, "qty": Decimal("1")}]).code, "line_supplier_mismatch")
        self.assertEqual(self.err([{"catalog_item": self.old, "qty": Decimal("1")}]).code, "line_inactive")

    def test_duplicate_items_are_rejected(self):
        e = self.err([{"catalog_item": self.ash, "qty": Decimal("1")}, {"catalog_item": self.ash, "qty": Decimal("2")}])
        self.assertEqual(e.code, "line_duplicate")

    def test_mulch_requires_base_seedlings_and_respects_4kg_per_tup(self):
        e = self.err([{"catalog_item": self.mul, "qty": Decimal("100")}])
        self.assertEqual(e.field, "base_seedlings")
        e = self.err([{"catalog_item": self.mul, "qty": Decimal("401")}], base_seedlings=100)
        self.assertEqual(e.code, "norm_violation")
        validate_lines([{"catalog_item": self.mul, "qty": Decimal("400")}], supplier_type="forest", base_seedlings=100)

    def test_fertilizer_5kg_per_tup_on_dm(self):
        self.err([{"catalog_item": self.bio, "qty": Decimal("501")}], supplier_type="dm", base_seedlings=100)
        validate_lines([{"catalog_item": self.bio, "qty": Decimal("500")}], supplier_type="dm", base_seedlings=100)

    def test_service_requires_problem_note(self):
        e = self.err([{"catalog_item": self.prot, "qty": Decimal("10")}], supplier_type="dm")
        self.assertEqual(e.field, "problem_note")
        validate_lines([{"catalog_item": self.prot, "qty": Decimal("10")}], supplier_type="dm", problem_note="Баргда доғ")


class SubmitValidationTest(TestCase):
    def setUp(self):
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.forest = make_forest()
        assign_forest(self.mahalla, self.forest)
        self.user = make_user("m", role="ym_mahalla")
        self.cab = member(self.user, YashilMembership.MemberType.MAHALLA, mahalla=self.mahalla)
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest,
                                          created_by_membership=self.cab, title="Кўчат", address="Манзил",
                                          lat=Decimal("41.3"), lon=Decimal("69.24"), area_ha=Decimal("0.5"))
        OrderLine.objects.create(order=self.order, catalog_item=self.ash, qty=Decimal("10"))

    def test_valid_order_passes(self):
        validate_for_submit(self.order)

    def test_map_point_is_required(self):
        self.order.lat = None
        with self.assertRaises(OrderValidationError) as cm:
            validate_for_submit(self.order)
        self.assertEqual(cm.exception.code, "map_required")

    def test_area_and_title_required(self):
        self.order.area_ha = None
        with self.assertRaises(OrderValidationError) as cm:
            validate_for_submit(self.order)
        self.assertEqual(cm.exception.field, "area_ha")
        self.order.area_ha = Decimal("0.5"); self.order.title = ""
        with self.assertRaises(OrderValidationError) as cm:
            validate_for_submit(self.order)
        self.assertEqual(cm.exception.field, "title")

    def test_area_mismatch_over_5_percent_needs_note(self):
        self.order.area_calc_ha = Decimal("0.6")
        with self.assertRaises(OrderValidationError) as cm:
            validate_for_submit(self.order)
        self.assertEqual(cm.exception.field, "area_note")
        self.order.area_note = "Чегара аниқлаштирилди"
        validate_for_submit(self.order)
        self.order.area_note = ""; self.order.area_calc_ha = Decimal("0.52")
        validate_for_submit(self.order)

    def test_repeat_order_requires_reason_and_link(self):
        self.order.linked_order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest,
                                                       created_by_membership=self.cab, title="Old")
        with self.assertRaises(OrderValidationError) as cm:
            validate_for_submit(self.order)
        self.assertEqual(cm.exception.field, "repeat_reason")
