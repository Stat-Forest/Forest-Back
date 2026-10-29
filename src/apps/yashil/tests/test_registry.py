"""Hisobot reestri (TZ §14.1–14.2; Q20, Q22): qator = buyurtma pozitsiyasi, ko'lam, filtrlar, unikal buyurtma soni."""
from datetime import date, datetime, timezone as tz
from decimal import Decimal

from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.yashil.models import Act, ActLine, ActVersion, Order, OrderLine, OrderState, YashilMembership
from apps.yashil.tests._common import (
    BASE, assign_forest, auth, make_district, make_dm, make_forest, make_item, make_mahalla, make_region, make_union,
    make_user, member, route_union,
)

T = YashilMembership.MemberType
D = lambda s: Decimal(s)  # noqa: E731


def ts(day, month=1, hour=9):
    return datetime(2027, month, day, hour, tzinfo=tz.utc)


class RegistryBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.region = make_region()
        self.district = make_district(self.region)
        self.region2 = make_region("1726", "Тошкент вилояти")
        self.district2 = make_district(self.region2, "1726262", "Чирчиқ")
        self.mahalla = make_mahalla(self.district, "Боғистон")
        self.mahalla2 = make_mahalla(self.district2, "Чирчиқ маҳалласи")
        self.forest = make_forest("Намуна ўрмон хўжалиги")
        self.forest2 = make_forest("Чирчиқ ўрмон хўжалиги")
        self.dm, p = make_dm("Яшил боғлар ДМ")
        assign_forest(self.mahalla, self.forest); assign_forest(self.mahalla2, self.forest2)
        self.unit = make_union(self.district); route_union(self.mahalla, self.unit)
        self.unit2 = make_union(self.district2, "Чирчиқ уюшмаси"); route_union(self.mahalla2, self.unit2)
        self.ash = make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup")
        self.mul = make_item("MUL", "Мульча", "forest", "mulch", "kg")
        self.bio = make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        self.m_user = make_user("m", role="ym_mahalla"); self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla)
        self.m2_user = make_user("m2", role="ym_mahalla"); self.m2_cab = member(self.m2_user, T.MAHALLA, mahalla=self.mahalla2)
        self.u_user = make_user("u", role="ym_union"); self.u_cab = member(self.u_user, T.UNION, union_unit=self.unit, can_sign=False)
        self.s_user = make_user("s", role="tashkilot_rahbari", organization=self.forest)
        self.s_cab = member(self.s_user, T.SUPPLIER, organization=self.forest)
        self.o_user = make_user("o", role="ym_observer")
        self.o_cab = member(self.o_user, T.OBSERVER, can_prepare=False, can_sign=False, observer_scope={"regions": [self.region.code]})
        self.o_all = make_user("oa", role="ym_observer")
        self.o_all_cab = member(self.o_all, T.OBSERVER, can_prepare=False, can_sign=False)

        # 1: o'rmon, ijroda, 2 qator, 1 approved akt (ASH 100), kechikkan
        self.o1 = self._order("YM-2027-000001", self.mahalla, self.forest, self.unit, "forest", OrderState.EXECUTION,
                              first=ts(10), accepted_on=date(2027, 1, 12), delivery_due=date(2027, 1, 26), late=2, stage="delivery")
        self.l1 = OrderLine.objects.create(order=self.o1, catalog_item=self.ash, qty=300, position=0)
        self.l1b = OrderLine.objects.create(order=self.o1, catalog_item=self.mul, qty=D("50.5"), position=1)
        self._approved_act(self.o1, "YM-2027-000001/A1", date(2027, 1, 20), [(self.l1, 100)])
        # 2: o'rmon, boshqa mahalla/xo'jalik, uyushmada yangi
        self.o2 = self._order("YM-2027-000002", self.mahalla2, self.forest2, self.unit2, "forest", OrderState.UNION_NEW, first=ts(15))
        OrderLine.objects.create(order=self.o2, catalog_item=self.ash, qty=200)
        # 3: DM, bajarilgan, shu mahalla
        self.o3 = self._order("YM-2027-000003", self.mahalla, self.dm, self.unit, "dm", OrderState.CLOSED, first=ts(5), accepted_on=date(2027, 1, 7))
        self.l3 = OrderLine.objects.create(order=self.o3, catalog_item=self.bio, qty=D("40"))
        self._approved_act(self.o3, "YM-2027-000003/A1", date(2027, 1, 9), [(self.l3, 40)])
        # 4: qoralama — reestrga kirmaydi
        self.o4 = self._order(None, self.mahalla, self.forest, None, "forest", OrderState.DRAFT)
        OrderLine.objects.create(order=self.o4, catalog_item=self.ash, qty=5)

    def _order(self, number, mahalla, org, unit, route, state, first=None, accepted_on=None, delivery_due=None, late=0, stage=""):
        return Order.objects.create(
            mahalla=mahalla, route=route, supplier_org=org, union_unit=unit, created_by_membership=self.m_cab if mahalla == self.mahalla else self.m2_cab,
            title=f"Буюртма {number or 'қоралама'}", address="Марказий кўча", number=number, state=state,
            lat=D("41.3"), lon=D("69.2"), area_ha=D("0.5"), first_submitted_at=first, last_submitted_at=first,
            accepted_on=accepted_on, accepted_at=ts(accepted_on.day) if accepted_on else None, delivery_due=delivery_due,
            late_workdays=late, overdue_stage=stage, executor_name="Ижрочи" if accepted_on else "",
        )

    def _approved_act(self, order, number, delivered, lines):
        act = Act.objects.create(order=order, index=1, number=number, status=Act.Status.APPROVED, approved_at=ts(delivered.day + 1))
        v = ActVersion.objects.create(act=act, version_no=1, delivery_date=delivered, submitted_at=ts(delivered.day))
        act.current_version = v; act.save()
        for line, qty in lines:
            ActLine.objects.create(act_version=v, order_line=line, qty=qty)
        return act

    def get(self, user, cab, path, **params):
        self.client.credentials()
        auth(self.client, user, cab)
        res = self.client.get(f"{BASE}/reports/{path}", params)
        self.assertEqual(res.status_code, 200, getattr(res, "data", res.content))
        return res.data


class RegistryScopeTest(RegistryBase):
    def test_row_per_line_and_drafts_excluded_for_mahalla(self):
        data = self.get(self.m_user, self.m_cab, "registry/")
        numbers = sorted((r["number"], r["item_code"]) for r in data["results"])
        self.assertEqual(numbers, [("YM-2027-000001", "ASH"), ("YM-2027-000001", "MUL"), ("YM-2027-000003", "BIO")])

    def test_other_mahalla_sees_only_its_own(self):
        data = self.get(self.m2_user, self.m2_cab, "registry/")
        self.assertEqual([r["number"] for r in data["results"]], ["YM-2027-000002"])

    def test_supplier_sees_only_forwarded_orders_of_its_org(self):
        data = self.get(self.s_user, self.s_cab, "registry/")
        self.assertEqual({r["number"] for r in data["results"]}, {"YM-2027-000001"})

    def test_observer_region_scope_and_republic(self):
        regional = self.get(self.o_user, self.o_cab, "registry/")
        self.assertEqual({r["number"] for r in regional["results"]}, {"YM-2027-000001", "YM-2027-000003"})
        republic = self.get(self.o_all, self.o_all_cab, "registry/")
        self.assertEqual({r["number"] for r in republic["results"]}, {"YM-2027-000001", "YM-2027-000002", "YM-2027-000003"})


class RegistryRowsTest(RegistryBase):
    def test_row_fields_accepted_and_remaining(self):
        data = self.get(self.o_all, self.o_all_cab, "registry/", q="000001", ordering="position")
        ash, mul = data["results"]
        self.assertEqual(ash["item"], "Шумтол кўчати")
        self.assertEqual(ash["unit_cyr"], "туп")
        self.assertEqual((ash["qty"], ash["accepted_qty"], ash["remaining_qty"]), ("300", "100", "200"))
        self.assertEqual((mul["qty"], mul["accepted_qty"], mul["remaining_qty"]), ("50.5", "0", "50.5"))
        self.assertEqual(ash["state_cyr"], "Ижрода")
        self.assertEqual(ash["route_cyr"], "Ўрмон хўжалиги")
        self.assertEqual(ash["mahalla"], "Боғистон")
        self.assertEqual(ash["supplier"], "Намуна ўрмон хўжалиги")
        self.assertEqual(ash["first_submitted_on"], "2027-01-10")
        self.assertEqual(ash["delivery_due"], "2027-01-26")
        self.assertEqual((ash["late_workdays"], ash["overdue_stage"]), (2, "delivery"))
        self.assertEqual(ash["act_numbers"], "YM-2027-000001/A1")
        self.assertEqual(ash["last_delivery_date"], "2027-01-20")
        self.assertEqual(ash["executor_name"], "Ижрочи")
        self.assertEqual(ash["row_no"], 1)
        self.assertEqual(mul["row_no"], 2)

    def test_filters(self):
        o = lambda **p: {r["number"] for r in self.get(self.o_all, self.o_all_cab, "registry/", **p)["results"]}  # noqa: E731
        self.assertEqual(o(route="dm"), {"YM-2027-000003"})
        self.assertEqual(o(state="union_new,closed"), {"YM-2027-000002", "YM-2027-000003"})
        self.assertEqual(o(catalog_item=str(self.mul.pk)), {"YM-2027-000001"})
        self.assertEqual(o(category="seedling"), {"YM-2027-000001", "YM-2027-000002"})
        self.assertEqual(o(overdue="1"), {"YM-2027-000001"})
        self.assertEqual(o(region=str(self.region2.pk)), {"YM-2027-000002"})
        self.assertEqual(o(district=str(self.district.pk)), {"YM-2027-000001", "YM-2027-000003"})
        self.assertEqual(o(mahalla=str(self.mahalla2.pk)), {"YM-2027-000002"})
        self.assertEqual(o(supplier_org=str(self.dm.pk)), {"YM-2027-000003"})
        self.assertEqual(o(q="Чирчиқ"), {"YM-2027-000002"})

    def test_period_basis(self):
        o = lambda **p: {r["number"] for r in self.get(self.o_all, self.o_all_cab, "registry/", **p)["results"]}  # noqa: E731
        self.assertEqual(o(date_from="2027-01-08", date_to="2027-01-12"), {"YM-2027-000001"})  # submitted (default)
        self.assertEqual(o(period_basis="accepted", date_from="2027-01-01", date_to="2027-01-08"), {"YM-2027-000003"})
        self.assertEqual(o(period_basis="delivered", date_from="2027-01-15", date_to="2027-01-31"), {"YM-2027-000001"})

    def test_invalid_period_basis_is_400(self):
        self.client.credentials(); auth(self.client, self.o_all, self.o_all_cab)
        res = self.client.get(f"{BASE}/reports/registry/", {"period_basis": "x"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["error_code"], "invalid_format")

    def test_ordering_and_pagination(self):
        data = self.get(self.o_all, self.o_all_cab, "registry/", ordering="-first_submitted_on", per_page=2)
        self.assertEqual(data["count"], 4)
        self.assertEqual([r["number"] for r in data["results"]], ["YM-2027-000002", "YM-2027-000001"])
        page2 = self.get(self.o_all, self.o_all_cab, "registry/", ordering="-first_submitted_on", per_page=2, page=2)
        self.assertEqual([r["row_no"] for r in page2["results"]], [3, 4])


class RegistrySummaryTest(RegistryBase):
    def test_unique_orders_and_item_totals(self):
        s = self.get(self.o_all, self.o_all_cab, "registry/summary/")
        self.assertEqual(s["orders"], 3)
        self.assertEqual(s["lines"], 4)
        by = {(i["item_code"]): i for i in s["by_item"]}
        self.assertEqual((by["ASH"]["ordered"], by["ASH"]["accepted"], by["ASH"]["remaining"]), ("500", "100", "400"))
        self.assertEqual(by["ASH"]["unit_cyr"], "туп")
        self.assertEqual(by["ASH"]["orders"], 2)
        self.assertEqual((by["MUL"]["ordered"], by["MUL"]["accepted"]), ("50.5", "0"))
        self.assertEqual(s["by_state"]["execution"], 1)
        self.assertEqual(s["by_state"]["closed"], 1)
        self.assertEqual(s["overdue_orders"], 1)

    def test_summary_respects_filters_and_scope(self):
        s = self.get(self.m_user, self.m_cab, "registry/summary/", route="forest")
        self.assertEqual(s["orders"], 1)
        self.assertEqual([i["item_code"] for i in s["by_item"]], ["ASH", "MUL"])


class ReportFiltersTest(RegistryBase):
    def test_dictionaries_in_scope(self):
        f = self.get(self.m_user, self.m_cab, "filters/")
        self.assertEqual({s["name"] for s in f["suppliers"]}, {"Намуна ўрмон хўжалиги", "Яшил боғлар ДМ"})
        self.assertEqual({i["code"] for i in f["items"]}, {"ASH", "MUL", "BIO"})
        self.assertIn({"value": "execution", "label": "Ижрода"}, f["states"])
        self.assertEqual([b["value"] for b in f["period_bases"]], ["submitted", "accepted", "delivered"])
