"""Xarita nuqtalari (TZ §15.4; Q24) va reestr/akt ro'yxati filtrlari (TZ §14.2)."""
from decimal import Decimal

from django.test import override_settings

from apps.yashil.models import Order, OrderState
from apps.yashil.tests._common import BASE, auth
from apps.yashil.tests.test_registry import RegistryBase, ts


class MapBase(RegistryBase):
    def setUp(self):
        super().setUp()
        Order.objects.filter(pk=self.o2.pk).update(lat=Decimal("41.0"), lon=Decimal("70.0"))
        self.o9 = self._order("YM-2027-000009", self.mahalla2, self.forest2, self.unit2, "forest", OrderState.PARTIAL, first=ts(12), accepted_on=ts(13).date())
        Order.objects.filter(pk=self.o9.pk).update(lat=Decimal("40.5"), lon=Decimal("71.0"))

    def get(self, user, cab, path, expect=200, **params):
        self.client.credentials(); auth(self.client, user, cab)
        res = self.client.get(f"{BASE}/{path}", params)
        self.assertEqual(res.status_code, expect, getattr(res, "data", res.content))
        return res.data


class MapPointsTest(MapBase):
    def test_only_accepted_partial_closed_with_coordinates(self):
        d = self.get(self.o_all, self.o_all_cab, "map/points/")
        self.assertEqual({p["number"] for p in d["points"]}, {"YM-2027-000001", "YM-2027-000003", "YM-2027-000009"})
        self.assertEqual(d["count"], 3)
        p1 = next(p for p in d["points"] if p["number"] == "YM-2027-000001")
        self.assertEqual((p1["lat"], p1["lon"]), ("41.3", "69.2"))
        self.assertEqual(p1["state"], "execution")
        self.assertEqual(p1["mahalla"], "Боғистон")
        self.assertEqual(p1["supplier"], "Намуна ўрмон хўжалиги")
        self.assertEqual(p1["area_ha"], "0.5")
        self.assertEqual(p1["lines"][0], {"item": "Шумтол кўчати", "item_lat": "Shumtol ko'chati", "unit_cyr": "туп", "qty": "300",
                                          "accepted": "100"})
        self.assertEqual((p1["delivery_due"], p1["late_workdays"]), ("2027-01-26", 2))

    def test_scope_and_filters(self):
        d = self.get(self.m_user, self.m_cab, "map/points/")
        self.assertEqual({p["number"] for p in d["points"]}, {"YM-2027-000001", "YM-2027-000003"})
        d = self.get(self.o_all, self.o_all_cab, "map/points/", route="dm")
        self.assertEqual([p["number"] for p in d["points"]], ["YM-2027-000003"])
        d = self.get(self.o_all, self.o_all_cab, "map/points/", state="partial")
        self.assertEqual([p["number"] for p in d["points"]], ["YM-2027-000009"])
        d = self.get(self.o_all, self.o_all_cab, "map/points/", bbox="40.0,70.5,41.0,71.5")
        self.assertEqual([p["number"] for p in d["points"]], ["YM-2027-000009"])

    def test_bad_bbox_is_400(self):
        res = self.get(self.o_all, self.o_all_cab, "map/points/", expect=400, bbox="x")
        self.assertEqual(res["field"], "bbox")

    @override_settings(YASHIL_MAP_MAX_POINTS=2)
    def test_too_many_points_requires_bbox(self):
        res = self.get(self.o_all, self.o_all_cab, "map/points/", expect=422)
        self.assertEqual(res["error_code"], "too_many_points")
        self.assertEqual(res["count"], 3)


class ListFiltersTest(MapBase):
    def test_orders_list_date_overdue_and_region_filters(self):
        d = self.get(self.o_all, self.o_all_cab, "orders/", overdue="1")
        self.assertEqual([o["number"] for o in d["results"]], ["YM-2027-000001"])
        d = self.get(self.o_all, self.o_all_cab, "orders/", date_from="2027-01-12", date_to="2027-01-15")
        self.assertEqual({o["number"] for o in d["results"]}, {"YM-2027-000002", "YM-2027-000009"})
        d = self.get(self.o_all, self.o_all_cab, "orders/", period_basis="accepted", date_from="2027-01-13", date_to="2027-01-13")
        self.assertEqual({o["number"] for o in d["results"]}, {"YM-2027-000009"})
        d = self.get(self.o_all, self.o_all_cab, "orders/", region=str(self.region2.pk))
        self.assertEqual({o["number"] for o in d["results"]}, {"YM-2027-000002", "YM-2027-000009"})
        d = self.get(self.o_all, self.o_all_cab, "orders/", supplier_org=str(self.dm.pk))
        self.assertEqual({o["number"] for o in d["results"]}, {"YM-2027-000003"})

    def test_orders_list_rows_carry_late_workdays(self):
        d = self.get(self.o_all, self.o_all_cab, "orders/", q="000001")
        self.assertEqual((d["results"][0]["late_workdays"], d["results"][0]["overdue_stage"]), (2, "delivery"))

    def test_acts_list_filters(self):
        d = self.get(self.o_all, self.o_all_cab, "acts/", date_from="2027-01-15", date_to="2027-01-25")
        self.assertEqual([a["number"] for a in d["results"]], ["YM-2027-000001/A1"])
        d = self.get(self.o_all, self.o_all_cab, "acts/", mahalla=str(self.mahalla.pk), route="dm")
        self.assertEqual([a["number"] for a in d["results"]], ["YM-2027-000003/A1"])
        d = self.get(self.o_all, self.o_all_cab, "acts/", supplier_org=str(self.forest.pk))
        self.assertEqual([a["number"] for a in d["results"]], ["YM-2027-000001/A1"])
        d = self.get(self.o_all, self.o_all_cab, "acts/", region=str(self.region.pk), status="approved")
        self.assertEqual(len(d["results"]), 2)
