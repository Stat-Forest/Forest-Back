"""Versiyali modul qoidalari (TZ §24.1): effective_from bilan yangi versiya, eski buyurtmalar qayta hisoblanmaydi."""
from datetime import date, datetime, timezone as tz
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from apps.yashil.models import Order, OrderLine, OrderState, ReviewSegment, YashilMembership, YashilSetting
from apps.yashil.services import deadlines, rules
from apps.yashil.services import transitions as tr
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_item, make_mahalla, make_region, make_union, make_user, member,
    route_union,
)

T = YashilMembership.MemberType


class RulesStoreTest(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user("adm", role="super_admin")

    def test_defaults_without_rows(self):
        self.assertEqual(rules.get("review_workdays"), 3)
        self.assertEqual(rules.get("delivery_workdays"), 10)
        self.assertEqual(rules.get("act_review_reminder_days"), 3)
        self.assertIs(rules.get("forest_negative_stock_allowed"), True)

    def test_new_version_applies_from_effective_date_only(self):
        rules.set_value("delivery_workdays", 12, user=self.admin, effective_from=date(2027, 3, 1), note="Қарор №5", today=date(2027, 2, 20))
        self.assertEqual(rules.get("delivery_workdays", on=date(2027, 2, 28)), 10)
        self.assertEqual(rules.get("delivery_workdays", on=date(2027, 3, 1)), 12)
        rules.set_value("delivery_workdays", 11, user=self.admin, effective_from=date(2027, 3, 1), today=date(2027, 2, 25))
        self.assertEqual(rules.get("delivery_workdays", on=date(2027, 3, 2)), 11)
        versions = list(YashilSetting.objects.filter(key="delivery_workdays").order_by("version").values_list("version", "value"))
        self.assertEqual(versions, [(1, 12), (2, 11)])

    def test_validation(self):
        with self.assertRaises(rules.RuleError):
            rules.set_value("delivery_workdays", 0, user=self.admin)
        with self.assertRaises(rules.RuleError):
            rules.set_value("delivery_workdays", "abc", user=self.admin)
        with self.assertRaises(rules.RuleError):
            rules.set_value("unknown_key", 1, user=self.admin)
        with self.assertRaises(rules.RuleError):
            rules.set_value("forest_negative_stock_allowed", "yes", user=self.admin)
        # o'tgan sanadan kuchga kiritish — yashirin qayta hisob bo'ladi, ruxsat yo'q
        with self.assertRaises(rules.RuleError):
            rules.set_value("review_workdays", 4, user=self.admin, effective_from=date(2027, 1, 1), today=date(2027, 2, 1))

    def test_snapshot_lists_current_and_history(self):
        rules.set_value("review_workdays", 4, user=self.admin, effective_from=date(2027, 3, 1), today=date(2027, 2, 1))
        snap = rules.snapshot(on=date(2027, 2, 15))
        row = next(r for r in snap if r["key"] == "review_workdays")
        self.assertEqual(row["value"], 3)
        self.assertEqual(row["default"], 3)
        self.assertEqual(row["pending"], [{"value": 4, "effective_from": "2027-03-01", "version": 1}])
        self.assertEqual(len(row["history"]), 1)


class RulesAppliedTest(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user("adm", role="super_admin")
        d = make_district(make_region())
        self.mahalla = make_mahalla(d)
        self.forest = make_forest(); assign_forest(self.mahalla, self.forest)
        self.unit = make_union(d); route_union(self.mahalla, self.unit)
        self.m = member(make_user("m", role="ym_mahalla"), T.MAHALLA, mahalla=self.mahalla)
        self.s = member(make_user("s", role="tashkilot_rahbari", organization=self.forest), T.SUPPLIER, organization=self.forest)
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")

    def _order(self, state, submitted_day):
        o = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest, union_unit=self.unit,
                                 created_by_membership=self.m, title="T", number=f"YM-2027-00000{submitted_day}", state=state,
                                 lat=Decimal("41.3"), lon=Decimal("69.2"), area_ha=Decimal("1"),
                                 first_submitted_at=datetime(2027, 1, submitted_day, 9, tzinfo=tz.utc))
        OrderLine.objects.create(order=o, catalog_item=self.ash, qty=10)
        ReviewSegment.objects.create(order=o, started_on=date(2027, 1, submitted_day))
        return o

    def test_review_days_follow_rule_effective_at_first_submission(self):
        rules.set_value("review_workdays", 5, user=self.admin, effective_from=date(2027, 1, 15), today=date(2027, 1, 1))
        old = self._order(OrderState.UNION_NEW, 11)   # 11-yanvar: 3 kun → 14-yanvar
        new = self._order(OrderState.UNION_NEW, 18)   # 18-yanvar: 5 kun → 25-yanvar
        self.assertEqual(deadlines.compute(old, date(2027, 1, 12), tr.calendar_from_db())["review_due"], date(2027, 1, 14))
        self.assertEqual(deadlines.compute(new, date(2027, 1, 19), tr.calendar_from_db())["review_due"], date(2027, 1, 25))
        self.assertEqual(tr.deadline_info(new, today=date(2027, 1, 19))["review_due"], "2027-01-25")

    def test_delivery_days_rule_used_on_accept(self):
        rules.set_value("delivery_workdays", 5, user=self.admin, effective_from=date(2027, 1, 18), today=date(2027, 1, 1))
        o = self._order(OrderState.SUPPLIER_REVIEW, 11)
        with patch("django.utils.timezone.now", return_value=datetime(2027, 1, 18, 9, tzinfo=tz.utc)):
            tr.accept(o, self.s, executor_name="Ижрочи")
        o.refresh_from_db()
        self.assertEqual(o.delivery_due, date(2027, 1, 25))  # 18 + 5 ish kuni

    def test_forest_negative_stock_policy(self):
        from apps.yashil.services.ledger import LedgerError

        rules.set_value("forest_negative_stock_allowed", False, user=self.admin, effective_from=date(2027, 1, 1), today=date(2027, 1, 1))
        o = self._order(OrderState.SUPPLIER_REVIEW, 11)
        with patch("django.utils.timezone.now", return_value=datetime(2027, 1, 18, 9, tzinfo=tz.utc)):
            with self.assertRaises(LedgerError) as ctx:
                tr.accept(o, self.s, executor_name="Ижрочи")
        self.assertEqual(ctx.exception.code, "stock_insufficient")
