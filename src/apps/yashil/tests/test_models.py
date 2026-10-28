"""Ma'lumotnoma modellari: cheklovlar va validatsiya (TZ §16, §20)."""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.yashil.models import CalendarDay, CatalogItem, Season, SupplierProfile, YashilMembership
from apps.yashil.services.units import quantity_error
from apps.yashil.services.workdays import CALENDAR_CACHE_KEY
from apps.yashil.tests._common import (
    assign_forest, make_district, make_dm, make_forest, make_item, make_mahalla, make_region, make_union,
    make_user, member, route_union,
)
from django.core.cache import cache


class SupplierAssignmentTest(TestCase):
    def setUp(self):
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.f1 = make_forest("F1 ўрмон хўжалиги")
        self.f2 = make_forest("F2 ўрмон хўжалиги")

    def test_second_open_ended_assignment_for_same_mahalla_is_rejected(self):
        assign_forest(self.mahalla, self.f1)
        with self.assertRaises(ValidationError):
            assign_forest(self.mahalla, self.f2)

    def test_overlapping_dated_assignment_is_rejected(self):
        assign_forest(self.mahalla, self.f1, date(2027, 1, 1), date(2027, 6, 30))
        with self.assertRaises(ValidationError):
            assign_forest(self.mahalla, self.f2, date(2027, 6, 1), None)

    def test_sequential_assignments_are_allowed(self):
        assign_forest(self.mahalla, self.f1, date(2027, 1, 1), date(2027, 6, 30))
        assign_forest(self.mahalla, self.f2, date(2027, 7, 1), None)

    def test_only_forest_supplier_can_be_assigned(self):
        dm, _ = make_dm()
        with self.assertRaises(ValidationError):
            assign_forest(self.mahalla, dm)


class UnionRouteTest(TestCase):
    def test_one_active_union_unit_per_mahalla(self):
        district = make_district(make_region())
        mahalla = make_mahalla(district)
        route_union(mahalla, make_union(district, "U1"))
        with self.assertRaises(ValidationError):
            route_union(mahalla, make_union(district, "U2"))


class MembershipTest(TestCase):
    def setUp(self):
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.user = make_user("u1")

    def test_mahalla_member_requires_mahalla(self):
        with self.assertRaises(ValidationError):
            member(self.user, YashilMembership.MemberType.MAHALLA)

    def test_supplier_member_requires_supplier_organization(self):
        org = make_forest()
        member(self.user, YashilMembership.MemberType.SUPPLIER, organization=org)
        plain = make_user("u2")
        from apps.yashil.tests._common import make_org
        with self.assertRaises(ValidationError):
            member(plain, YashilMembership.MemberType.SUPPLIER, organization=make_org("Oddiy tashkilot"))

    def test_mahalla_member_must_not_carry_organization(self):
        with self.assertRaises(ValidationError):
            member(self.user, YashilMembership.MemberType.MAHALLA, mahalla=self.mahalla, organization=make_forest())

    def test_observer_scope_defaults_to_republic(self):
        m = member(self.user, YashilMembership.MemberType.OBSERVER, can_prepare=False, can_sign=False)
        self.assertEqual(m.observer_scope, {})
        self.assertTrue(m.is_current())

    def test_expired_membership_is_not_current(self):
        m = member(self.user, YashilMembership.MemberType.MAHALLA, mahalla=self.mahalla,
                   valid_from=date(2026, 1, 1), valid_to=date(2026, 6, 30))
        self.assertFalse(m.is_current(date(2027, 1, 1)))


class SupplierProfileTest(TestCase):
    def test_dm_branch_parent_must_be_dm(self):
        forest = make_forest()
        with self.assertRaises(ValidationError):
            make_dm("ДМ бўлинма", parent=forest)

    def test_forest_profile_cannot_have_parent(self):
        dm, _ = make_dm()
        with self.assertRaises(ValidationError):
            make_forest("Бола хўжалик", parent=dm.supplier_profile)


class CatalogAndUnitsTest(TestCase):
    def test_precision_follows_unit(self):
        tup = make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup")
        kg = make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        ha = make_item("SRV", "Ҳимоя хизмати", "dm", "protection_service", "ga", item_type="service")
        self.assertEqual((tup.precision, kg.precision, ha.precision), (0, 3, 4))

    def test_quantity_validation_by_unit(self):
        self.assertIsNone(quantity_error(Decimal("10"), "tup"))
        self.assertIsNotNone(quantity_error(Decimal("10.5"), "tup"))
        self.assertIsNone(quantity_error(Decimal("2.125"), "kg"))
        self.assertIsNotNone(quantity_error(Decimal("2.1234"), "kg"))
        self.assertIsNone(quantity_error(Decimal("0.0001"), "ga"))
        self.assertIsNotNone(quantity_error(Decimal("0"), "ga"))
        self.assertIsNotNone(quantity_error(Decimal("-1"), "dona"))

    def test_service_item_must_be_dm(self):
        with self.assertRaises(ValidationError):
            make_item("X", "Хизмат", "forest", "protection_service", "daraxt", item_type="service")

    def test_forest_catalog_limited_to_seedling_and_mulch(self):
        make_item("MUL", "Мульча", "forest", "mulch", "kg")
        with self.assertRaises(ValidationError):
            make_item("BIO2", "Биогумус", "forest", "fertilizer", "kg")

    def test_season_unique_per_year_and_kind(self):
        Season.objects.create(year=2027, kind=Season.Kind.SPRING, date_from=date(2027, 3, 1), date_to=date(2027, 5, 31))
        with self.assertRaises(ValidationError):
            Season.objects.create(year=2027, kind=Season.Kind.SPRING, date_from=date(2027, 3, 2), date_to=date(2027, 5, 30))


class CalendarDayTest(TestCase):
    def test_saving_a_day_invalidates_calendar_cache(self):
        cache.set(CALENDAR_CACHE_KEY, "stale", 600)
        CalendarDay.objects.create(date=date(2027, 1, 11), kind=CalendarDay.Kind.HOLIDAY, note="test")
        self.assertIsNone(cache.get(CALENDAR_CACHE_KEY))
