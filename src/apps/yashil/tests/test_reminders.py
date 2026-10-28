"""Muddat eslatmalari (TZ §8.2; javob Д5): 1 ish kuni qolganda, buzilganda va kechikish davom etganda har kun."""
from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase

from apps.yashil.models import Order, OrderLine, OrderState, ReviewSegment, YashilMembership, YashilNotification
from apps.yashil.tasks import deadline_reminders
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_item, make_mahalla, make_region, make_union, make_user, member,
    route_union,
)

T = YashilMembership.MemberType


class ReminderTest(TestCase):
    def setUp(self):
        cache.clear()
        d = make_district(make_region())
        self.mahalla = make_mahalla(d)
        self.forest = make_forest(); assign_forest(self.mahalla, self.forest)
        self.unit = make_union(d); route_union(self.mahalla, self.unit)
        self.m = member(make_user("m", role="ym_mahalla"), T.MAHALLA, mahalla=self.mahalla)
        self.u = member(make_user("u", role="ym_union"), T.UNION, union_unit=self.unit, can_sign=False)
        self.s = member(make_user("s", role="tashkilot_rahbari", organization=self.forest), T.SUPPLIER, organization=self.forest)
        self.o = member(make_user("o", role="ym_observer"), T.OBSERVER, can_prepare=False, can_sign=False)
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest, union_unit=self.unit,
                                          created_by_membership=self.m, title="T", number="YM-2027-000001",
                                          state=OrderState.UNION_NEW, lat=Decimal("41.3"), lon=Decimal("69.2"), area_ha=Decimal("1"))
        OrderLine.objects.create(order=self.order, catalog_item=make_item("ASH", "Шумтол", "forest", "seedling", "tup"), qty=10)
        ReviewSegment.objects.create(order=self.order, started_on=date(2027, 1, 11))  # muddat: 14-yanvar

    def kinds(self, user):
        return list(YashilNotification.objects.filter(recipient_user=user.user).order_by("id").values_list("kind", flat=True))

    def test_review_reminder_one_day_before_goes_to_responsible(self):
        deadline_reminders(today=date(2027, 1, 13))
        self.assertEqual(self.kinds(self.u), ["deadline_reminder"])
        self.assertEqual(self.kinds(self.s), [])
        self.assertEqual(self.kinds(self.m), [])

    def test_overdue_notifies_responsible_and_observers_daily_but_once_per_day(self):
        deadline_reminders(today=date(2027, 1, 15))
        deadline_reminders(today=date(2027, 1, 15))
        self.assertEqual(self.kinds(self.u), ["overdue"])
        self.assertEqual(self.kinds(self.o), ["overdue"])
        deadline_reminders(today=date(2027, 1, 18))
        self.assertEqual(self.kinds(self.u), ["overdue", "overdue"])

    def test_delivery_reminders_three_and_one_day_before_and_overdue(self):
        self.order.state = OrderState.EXECUTION
        self.order.delivery_due = date(2027, 1, 25)
        self.order.save()
        ReviewSegment.objects.filter(order=self.order).update(ended_on=date(2027, 1, 11))
        deadline_reminders(today=date(2027, 1, 20))  # 3 ish kuni qoldi (21, 22, 25)
        deadline_reminders(today=date(2027, 1, 22))  # 1 ish kuni qoldi
        deadline_reminders(today=date(2027, 1, 26))  # buzildi
        self.assertEqual(self.kinds(self.s), ["deadline_reminder", "deadline_reminder", "overdue"])
        self.assertEqual(self.kinds(self.u), [])
        self.assertEqual(self.kinds(self.m), ["overdue"])

    def test_nothing_on_quiet_days(self):
        deadline_reminders(today=date(2027, 1, 12))
        self.assertEqual(YashilNotification.objects.count(), 0)


class ActReviewReminderTest(ReminderTest):
    def test_act_in_mahalla_review_over_three_workdays_reminds_mahalla(self):
        from datetime import datetime, timezone as tz

        from apps.yashil.models import Act, ActVersion

        self.order.state = OrderState.EXECUTION; self.order.save()
        act = Act.objects.create(order=self.order, index=1, number="YM-2027-000001/A1", status=Act.Status.REVIEW)
        v = ActVersion.objects.create(act=act, version_no=1, delivery_date=date(2027, 1, 12), submitted_at=datetime(2027, 1, 12, 9, tzinfo=tz.utc))
        act.current_version = v; act.save()
        deadline_reminders(today=date(2027, 1, 15))  # 3 ish kuni: 13, 14, 15 — hali muddat ichida
        self.assertEqual(self.kinds(self.m), [])
        deadline_reminders(today=date(2027, 1, 18))
        deadline_reminders(today=date(2027, 1, 18))
        self.assertEqual(self.kinds(self.m), ["deadline_reminder"])
        self.assertEqual(self.kinds(self.s), [])
