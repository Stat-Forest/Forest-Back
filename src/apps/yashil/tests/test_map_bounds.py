"""Buyurtma xaritasi: mahalla viloyatida ochiladi, O'zbekistondan tashqaridagi nuqta yuborilmaydi."""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APITestCase

from apps.billing.models import XojalikLocation
from apps.yashil.models import Order, OrderLine, YashilMembership
from apps.yashil.services import norms
from apps.yashil.services.norms import OrderValidationError, validate_for_submit
from apps.yashil.tests._common import (
    BASE, assign_forest, auth, make_district, make_forest, make_item, make_mahalla, make_region, make_user, member,
)


def location(region, name, bounds):
    return XojalikLocation.objects.create(name=name, region=region, latitude=Decimal("40"), longitude=Decimal("70"), bounds=bounds)


class SubmitPointLimitsTest(TestCase):
    def setUp(self):
        mahalla = make_mahalla(make_district(make_region()))
        forest = make_forest()
        assign_forest(mahalla, forest)
        cab = member(make_user("m", role="ym_mahalla"), YashilMembership.MemberType.MAHALLA, mahalla=mahalla)
        self.order = Order.objects.create(mahalla=mahalla, route="forest", supplier_org=forest, created_by_membership=cab,
                                          title="Кўчат", address="Манзил", lat=Decimal("40.78"), lon=Decimal("72.34"),
                                          area_ha=Decimal("0.5"))
        OrderLine.objects.create(order=self.order, catalog_item=make_item("ASH", "Шумтол", "forest", "seedling", "tup"), qty=Decimal("10"))

    def test_points_inside_uzbekistan_pass(self):
        # Termiz (janub), Nukus (g'arb), Andijon (sharq)
        for lat, lon in (("37.22", "67.28"), ("42.46", "59.61"), ("40.78", "72.34")):
            self.order.lat, self.order.lon = Decimal(lat), Decimal(lon)
            validate_for_submit(self.order)

    def test_point_outside_uzbekistan_is_rejected(self):
        # Moskva, Olmaota, Ashxoboddan janub, 0/0 (bo'sh xarita bosilgan)
        for lat, lon in (("55.75", "37.61"), ("43.24", "76.89"), ("36.5", "58.0"), ("0", "0")):
            self.order.lat, self.order.lon = Decimal(lat), Decimal(lon)
            with self.assertRaises(OrderValidationError) as cm:
                validate_for_submit(self.order)
            self.assertEqual((cm.exception.code, cm.exception.field), ("map_outside", "lat"))


class RegionBoundsTest(TestCase):
    def test_union_of_region_forest_areas(self):
        andijon, other = make_region(), make_region("1730", "Фарғона вилояти")
        location(andijon, "A", [[40.4, 71.6], [40.9, 72.5]])
        location(andijon, "B", [[40.6, 72.2], [41.0, 73.1]])
        location(andijon, "Buzuq", None)
        location(andijon, "Buzuq 2", [[1, 2]])
        location(other, "F", [[40.0, 70.5], [40.6, 71.5]])
        self.assertEqual(norms.region_bounds(andijon.id), [[40.4, 71.6], [41.0, 73.1]])

    def test_clamped_to_country_and_none_without_data(self):
        region = make_region()
        self.assertIsNone(norms.region_bounds(region.id))
        location(region, "Chet", [[30.0, 50.0], [50.0, 80.0]])
        self.assertEqual(norms.region_bounds(region.id), norms.UZ_BOUNDS)


class SuppliersForMahallaMapTest(APITestCase):
    def test_response_carries_map_bounds_and_limits(self):
        region = make_region()
        mahalla = make_mahalla(make_district(region))
        location(region, "A", [[40.4, 71.6], [41.0, 73.1]])
        user = make_user("m", role="ym_mahalla")
        auth(self.client, user, member(user, YashilMembership.MemberType.MAHALLA, mahalla=mahalla))
        res = self.client.get(f"{BASE}/suppliers/for-mahalla/{mahalla.id}/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["map"], {"bounds": [[40.4, 71.6], [41.0, 73.1]], "limits": norms.UZ_BOUNDS})
