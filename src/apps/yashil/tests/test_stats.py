"""Statistika (TZ §15.1–15.3; javob З3): kartalar, ko'chatlar farqi, orqada qolayotgan tashkilotlar, kesh."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache

from apps.yashil.models import Act, ActLine, ActVersion, OrderLine, OrderState, ReviewSegment
from apps.yashil.services import stats
from apps.yashil.tests._common import BASE, auth
from apps.yashil.tests.test_registry import RegistryBase, ts


class StatsBase(RegistryBase):
    def setUp(self):
        super().setUp()
        # 5: mahallaga qaytarilgan (ASH 70) — «Қайтарилган», ko'chat ehtiyoji alohida
        self.o5 = self._order("YM-2027-000005", self.mahalla, self.forest, self.unit, "forest", OrderState.RETURNED, first=ts(16))
        OrderLine.objects.create(order=self.o5, catalog_item=self.ash, qty=70)
        # 6: uyushma ko'rib chiqmoqda, kechikkan 3 kun (uyushma masʼul)
        self.o6 = self._order("YM-2027-000006", self.mahalla, self.forest, self.unit, "forest", OrderState.UNION_REVIEW, first=ts(11), late=3, stage="review")
        ReviewSegment.objects.create(order=self.o6, started_on=date(2027, 1, 11))
        OrderLine.objects.create(order=self.o6, catalog_item=self.ash, qty=10)
        # 7: yetkazib beruvchida yangi (kechikmagan)
        self.o7 = self._order("YM-2027-000007", self.mahalla2, self.forest2, self.unit2, "forest", OrderState.SUPPLIER_NEW, first=ts(18))
        OrderLine.objects.create(order=self.o7, catalog_item=self.mul, qty=5)
        # 8: bekor qilingan — hech qayerga kirmaydi (ko'chat 1000)
        self.o8 = self._order("YM-2027-000008", self.mahalla, self.forest, self.unit, "forest", OrderState.CANCELLED, first=ts(3))
        OrderLine.objects.create(order=self.o8, catalog_item=self.ash, qty=1000)
        # o1 bo'yicha mahalla tasdig'idagi akt (ASH 50) — «Тасдиқ кутилмоқда»
        act = Act.objects.create(order=self.o1, index=2, number="YM-2027-000001/A2", status=Act.Status.REVIEW)
        v = ActVersion.objects.create(act=act, version_no=1, delivery_date=date(2027, 1, 22), submitted_at=ts(22))
        act.current_version = v; act.save()
        ActLine.objects.create(act_version=v, order_line=self.l1, qty=50)
        cache.clear()

    def api(self, user, cab, path, **params):
        self.client.credentials(); auth(self.client, user, cab)
        res = self.client.get(f"{BASE}/stats/{path}", params)
        self.assertEqual(res.status_code, 200, getattr(res, "data", res.content))
        return res.data


class CardsTest(StatsBase):
    def test_cards_follow_tz_rules(self):
        c = stats.cards(self.o_all_cab, False, stats.parse({}))
        self.assertEqual(c["total"], 7)  # qoralama kirmaydi
        self.assertEqual((c["new"], c["new_union"], c["new_supplier"]), (2, 1, 1))  # o2 union_new, o7 supplier_new
        self.assertEqual(c["reviewing"], 1)  # o6
        self.assertEqual(c["reviewed"], 1)   # o1 execution
        self.assertEqual(c["done"], 1)       # o3
        self.assertEqual(c["returned"], 1)   # o5
        self.assertEqual(c["cancelled"], 1)  # o8
        self.assertEqual((c["overdue"], c["overdue_review"], c["overdue_delivery"]), (2, 1, 1))
        self.assertEqual(c["new"] + c["reviewing"] + c["reviewed"] + c["done"] + c["returned"] + c["cancelled"], c["total"])

    def test_cards_scope_and_filters(self):
        c = stats.cards(self.m_cab, False, stats.parse({}))
        self.assertEqual(c["total"], 5)  # o1, o3, o5, o6, o8
        c = stats.cards(self.o_all_cab, False, stats.parse({"route": "dm"}))
        self.assertEqual((c["total"], c["done"]), (1, 1))
        c = stats.cards(self.o_all_cab, False, stats.parse({"date_from": "2027-01-15", "date_to": "2027-01-18"}))
        self.assertEqual(c["total"], 3)  # o2 (15), o5 (16), o7 (18)

    def test_api_cards_for_mahalla(self):
        d = self.api(self.m_user, self.m_cab, "cards/")
        self.assertEqual(d["total"], 5)
        self.assertEqual(d["filters_label"], "Buyurtma yuborilgan sana (birinchi yuborish)")


class SeedlingsTest(StatsBase):
    def test_ordered_accepted_pending_returned(self):
        s = stats.seedlings(self.o_all_cab, False, stats.parse({}))
        ash = next(r for r in s["items"] if r["item_code"] == "ASH")
        # buyurtma: o1 300 + o2 200 + o5 70 + o6 10 = 580 (bekor 1000 va qoralama 5 kirmaydi)
        self.assertEqual(ash["ordered"], "580")
        self.assertEqual(ash["accepted"], "100")
        self.assertEqual(ash["pending"], "50")
        self.assertEqual(ash["returned_open"], "70")
        self.assertEqual(ash["diff"], "480")
        self.assertEqual(ash["unit_cyr"], "туп")
        self.assertEqual(s["totals"]["ordered"], "580")
        self.assertEqual(s["totals"]["pending"], "50")
        self.assertEqual([r["item_code"] for r in s["items"]], ["ASH"])  # faqat ko'chat kategoriyasi

    def test_seedlings_period_accepted_basis(self):
        s = stats.seedlings(self.o_all_cab, False, stats.parse({"period_basis": "accepted", "date_from": "2027-01-12", "date_to": "2027-01-12"}))
        ash = next(r for r in s["items"] if r["item_code"] == "ASH")
        self.assertEqual((ash["ordered"], ash["accepted"]), ("300", "100"))


class OrganizationsTest(StatsBase):
    def test_lag_table_attributes_lateness_to_holder(self):
        rows = stats.organizations(self.o_all_cab, False, stats.parse({}))
        by = {(r["kind"], r["name"]): r for r in rows}
        forest = by[("supplier", "Намуна ўрмон хўжалиги")]
        self.assertEqual((forest["total"], forest["in_progress"], forest["done"]), (4, 1, 0))  # o1, o5, o6, o8 (o8 bekor)
        self.assertEqual((forest["review_late"], forest["delivery_late"], forest["max_late_days"]), (0, 1, 2))
        self.assertTrue(forest["has_late"])
        union = by[("union", "Андижон туман уюшмаси")]
        self.assertEqual((union["review_late"], union["max_late_days"]), (1, 3))
        self.assertTrue(union["has_late"])
        dm = by[("supplier", "Яшил боғлар ДМ")]
        self.assertEqual((dm["total"], dm["done"], dm["done_pct"], dm["has_late"]), (1, 1, "100.0", False))
        forest2 = by[("supplier", "Чирчиқ ўрмон хўжалиги")]
        self.assertFalse(forest2["has_late"])
        # kechikkanlar tepada
        self.assertTrue(rows[0]["has_late"] and rows[1]["has_late"])

    def test_api_organizations_observer(self):
        rows = self.api(self.o_user, self.o_cab, "organizations/")["results"]
        self.assertEqual({r["name"] for r in rows}, {"Намуна ўрмон хўжалиги", "Яшил боғлар ДМ", "Андижон туман уюшмаси"})


class CacheTest(StatsBase):
    def test_second_call_is_cached_and_version_bump_invalidates(self):
        f = stats.parse({})
        stats.cards(self.o_all_cab, False, f)
        with patch.object(stats, "_cards", side_effect=AssertionError("DB ga murojaat bo'lmasligi kerak")):
            cached = stats.cards(self.o_all_cab, False, f)
        self.assertEqual(cached["total"], 7)
        stats.bump_version()
        self.o2.state = OrderState.CANCELLED; self.o2.save()
        self.assertEqual(stats.cards(self.o_all_cab, False, f)["cancelled"], 2)

    def test_cache_key_differs_by_cabinet(self):
        f = stats.parse({})
        self.assertEqual(stats.cards(self.o_all_cab, False, f)["total"], 7)
        self.assertEqual(stats.cards(self.m_cab, False, f)["total"], 5)
