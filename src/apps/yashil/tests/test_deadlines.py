"""Kechikish tungi hisobi: Order.review_due / late_workdays / overdue_stage (TZ §14.2 filtr, §15.1 karta; Q23)."""
from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from apps.yashil.models import CalendarDay, Order, OrderLine, OrderState, ReviewSegment, YashilMembership
from apps.yashil.services import deadlines, transitions as tr
from apps.yashil.tasks import deadline_reminders
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_item, make_mahalla, make_region, make_union, make_user, member,
    route_union,
)

T = YashilMembership.MemberType


class DeadlineRecalcTest(TestCase):
    def setUp(self):
        cache.clear()
        d = make_district(make_region())
        self.mahalla = make_mahalla(d)
        self.forest = make_forest(); assign_forest(self.mahalla, self.forest)
        self.unit = make_union(d); route_union(self.mahalla, self.unit)
        self.m = member(make_user("m", role="ym_mahalla"), T.MAHALLA, mahalla=self.mahalla)
        self.u = member(make_user("u", role="ym_union"), T.UNION, union_unit=self.unit, can_sign=False)
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest, union_unit=self.unit,
                                          created_by_membership=self.m, title="T", number="YM-2027-000001",
                                          state=OrderState.UNION_REVIEW, lat=Decimal("41.3"), lon=Decimal("69.2"), area_ha=Decimal("1"))
        OrderLine.objects.create(order=self.order, catalog_item=make_item("ASH", "Шумтол", "forest", "seedling", "tup"), qty=10)
        ReviewSegment.objects.create(order=self.order, started_on=date(2027, 1, 11))  # muddat: 14-yanvar (chorshanba)

    def test_review_within_deadline_has_due_and_no_lateness(self):
        info = deadlines.recalc_order(self.order, today=date(2027, 1, 13))
        self.order.refresh_from_db()
        self.assertEqual(self.order.review_due, date(2027, 1, 14))
        self.assertEqual(self.order.late_workdays, 0)
        self.assertEqual(self.order.overdue_stage, "")
        self.assertEqual(info["late_workdays"], 0)

    def test_review_overdue_counts_workdays_after_due(self):
        deadlines.recalc_order(self.order, today=date(2027, 1, 18))  # 15 (juma), 18 (dushanba)
        self.order.refresh_from_db()
        self.assertEqual(self.order.late_workdays, 2)
        self.assertEqual(self.order.overdue_stage, "review")

    def test_holiday_from_calendar_is_skipped(self):
        CalendarDay.objects.create(date=date(2027, 1, 15), kind=CalendarDay.Kind.HOLIDAY)
        deadlines.recalc_order(self.order, today=date(2027, 1, 18))
        self.order.refresh_from_db()
        self.assertEqual(self.order.late_workdays, 1)

    def test_delivery_overdue(self):
        self.order.state = OrderState.EXECUTION
        self.order.delivery_due = date(2027, 1, 25)
        self.order.save()
        ReviewSegment.objects.filter(order=self.order).update(ended_on=date(2027, 1, 11))
        deadlines.recalc_order(self.order, today=date(2027, 1, 27))
        self.order.refresh_from_db()
        self.assertEqual(self.order.late_workdays, 2)
        self.assertEqual(self.order.overdue_stage, "delivery")
        self.assertIsNone(self.order.review_due)

    def test_final_state_is_never_late(self):
        self.order.state = OrderState.CLOSED
        self.order.delivery_due = date(2027, 1, 25)
        self.order.late_workdays = 5
        self.order.overdue_stage = "delivery"
        self.order.save()
        deadlines.recalc_order(self.order, today=date(2027, 2, 10))
        self.order.refresh_from_db()
        self.assertEqual(self.order.late_workdays, 0)
        self.assertEqual(self.order.overdue_stage, "")

    def test_transition_resets_lateness(self):
        deadlines.recalc_order(self.order, today=date(2027, 1, 18))
        self.order.refresh_from_db()
        self.assertEqual(self.order.late_workdays, 2)
        tr.return_order(self.order, self.u, reason_code="lines", comment="Миқдор")
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, OrderState.RETURNED)
        self.assertEqual(self.order.late_workdays, 0)
        self.assertIsNone(self.order.review_due)

    def test_recalc_all_updates_only_changed_rows_and_reminders_call_it(self):
        changed = deadlines.recalc_all(today=date(2027, 1, 18))
        self.assertEqual(changed, 1)
        self.assertEqual(deadlines.recalc_all(today=date(2027, 1, 18)), 0)
        deadline_reminders(today=date(2027, 1, 19))
        self.order.refresh_from_db()
        self.assertEqual(self.order.late_workdays, 3)

    def test_management_command(self):
        out = StringIO()
        call_command("yashil_recalc_deadlines", "--today", "2027-01-18", stdout=out)
        self.order.refresh_from_db()
        self.assertEqual(self.order.late_workdays, 2)
        self.assertIn("1", out.getvalue())
