"""Holat mashinasi: kim, qaysi holatdan, nima yozadi (TZ §6, §7, §8.1; Q07, Q08, Q10, Q14)."""
from datetime import date, datetime, timezone as tz
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from apps.yashil.models import Order, OrderLine, OrderState, ReturnReason, YashilMembership, YashilNotification
from apps.yashil.services import transitions as tr
from apps.yashil.services.transitions import TransitionError
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_item, make_mahalla, make_region, make_union, make_user, member,
    route_union,
)

T = YashilMembership.MemberType


def at(day, hour=9):
    return datetime(2027, 1, day, hour, tzinfo=tz.utc)


class TransitionTest(TestCase):
    def setUp(self):
        cache.clear()
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.forest = make_forest()
        assign_forest(self.mahalla, self.forest)
        self.unit = make_union(self.district)
        route_union(self.mahalla, self.unit)
        self.m_user = make_user("m", role="ym_mahalla"); self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla)
        self.u_user = make_user("u", role="ym_union"); self.u_cab = member(self.u_user, T.UNION, union_unit=self.unit, can_sign=False)
        self.u2_user = make_user("u2", role="ym_union"); member(self.u2_user, T.UNION, union_unit=self.unit, can_sign=False)
        self.s_user = make_user("s", role="tashkilot_hodimi", organization=self.forest)
        self.s_cab = member(self.s_user, T.SUPPLIER, organization=self.forest, can_sign=False)
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest,
                                          created_by_membership=self.m_cab, title="Кўчат", address="Манзил",
                                          lat=Decimal("41.3"), lon=Decimal("69.24"), area_ha=Decimal("0.5"))
        OrderLine.objects.create(order=self.order, catalog_item=self.ash, qty=Decimal("10"))

    def submit(self, when=at(11)):
        with patch("django.utils.timezone.now", return_value=when):
            return tr.submit(self.order, self.m_cab, document_version=None)

    def test_submit_numbers_order_opens_segment_and_notifies_union(self):
        self.submit()
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, OrderState.UNION_NEW)
        self.assertEqual(self.order.number, "YM-2027-000001")
        self.assertEqual(self.order.union_unit, self.unit)
        self.assertEqual(self.order.review_segments_as_tuples(), [("2027-01-11", None)])
        self.assertEqual(self.order.versions.count(), 1)
        self.assertEqual(self.order.versions.get().snapshot["lines"][0]["qty"], "10")
        self.assertEqual(YashilNotification.objects.filter(kind="order_new_union").count(), 2)
        self.assertEqual(self.order.events.get(action="submit").to_state, OrderState.UNION_NEW)

    def test_submit_without_union_route_fails(self):
        self.mahalla.union_routes.all().delete()
        with self.assertRaises(TransitionError) as cm:
            self.submit()
        self.assertEqual(cm.exception.code, "union_not_routed")

    def test_only_mahalla_signer_can_submit(self):
        with self.assertRaises(TransitionError):
            tr.submit(self.order, self.u_cab, document_version=None)
        self.m_cab.can_sign = False; self.m_cab.save()
        with self.assertRaises(TransitionError) as cm:
            self.submit()
        self.assertEqual(cm.exception.code, "cannot_sign")

    def test_union_review_forward_and_supplier_accept(self):
        self.submit()
        tr.start_review(self.order, self.u_cab)
        self.assertEqual(self.order.state, OrderState.UNION_REVIEW)
        with self.assertRaises(TransitionError) as cm:
            tr.start_review(self.order, self.s_cab)
        self.assertEqual(cm.exception.code, "state_conflict")
        tr.forward(self.order, self.u_cab)
        self.assertEqual(self.order.state, OrderState.SUPPLIER_NEW)
        self.assertTrue(YashilNotification.objects.filter(kind="order_forwarded", recipient_user=self.s_user).exists())
        tr.start_review(self.order, self.s_cab)
        with patch("django.utils.timezone.now", return_value=at(12)):
            tr.accept(self.order, self.s_cab, executor_name="Иброҳимов")
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, OrderState.EXECUTION)
        self.assertEqual(self.order.accepted_on, date(2027, 1, 12))
        self.assertEqual(self.order.delivery_due, date(2027, 1, 26))
        self.assertEqual(self.order.review_segments_as_tuples(), [("2027-01-11", "2027-01-12")])
        self.assertTrue(YashilNotification.objects.filter(kind="order_accepted", recipient_user=self.m_user).exists())

    def test_q07_return_requires_comment(self):
        self.submit(); tr.start_review(self.order, self.u_cab)
        with self.assertRaises(TransitionError) as cm:
            tr.return_order(self.order, self.u_cab, reason_code=ReturnReason.ADDRESS, comment="  ")
        self.assertEqual(cm.exception.field, "comment")

    def test_q14_return_pauses_review_and_resubmit_keeps_number_new_version(self):
        self.submit(at(11)); tr.start_review(self.order, self.u_cab)
        with patch("django.utils.timezone.now", return_value=at(12)):
            tr.return_order(self.order, self.u_cab, reason_code=ReturnReason.ADDRESS, comment="Манзилни аниқлаштиринг", fields=["address"])
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, OrderState.RETURNED)
        self.assertEqual(self.order.review_segments_as_tuples(), [("2027-01-11", "2027-01-12")])
        self.assertTrue(YashilNotification.objects.filter(kind="order_returned", recipient_user=self.m_user).exists())
        self.order.address = "Янги манзил"; self.order.save()
        with patch("django.utils.timezone.now", return_value=at(15)):
            tr.submit(self.order, self.m_cab, document_version=None)
        self.order.refresh_from_db()
        self.assertEqual(self.order.number, "YM-2027-000001")
        self.assertEqual(self.order.version_no, 2)
        self.assertEqual(self.order.versions.count(), 2)
        self.assertIsNotNone(self.order.versions.get(version_no=1).superseded_at)
        self.assertEqual(self.order.review_segments_as_tuples(), [("2027-01-11", "2027-01-12"), ("2027-01-15", None)])
        self.assertEqual(tr.review_due(self.order), date(2027, 1, 19))

    def test_q10_supplier_return_goes_to_mahalla_and_notifies_union(self):
        self.submit(); tr.start_review(self.order, self.u_cab); tr.forward(self.order, self.u_cab); tr.start_review(self.order, self.s_cab)
        tr.return_order(self.order, self.s_cab, reason_code=ReturnReason.LINES, comment="Кўчат тури мос эмас")
        self.assertEqual(self.order.state, OrderState.RETURNED)
        kinds = set(YashilNotification.objects.filter(kind="order_returned").values_list("recipient_user__email", flat=True))
        self.assertEqual(kinds, {"m@example.com", "u@example.com", "u2@example.com"})

    def test_allowed_actions_per_cabinet(self):
        self.assertEqual(tr.allowed_actions(self.order, self.m_cab), ["edit", "submit"])
        self.assertEqual(tr.allowed_actions(self.order, self.u_cab), [])
        self.submit()
        self.assertEqual(tr.allowed_actions(self.order, self.u_cab), ["review"])
        self.assertEqual(tr.allowed_actions(self.order, self.m_cab), [])
        tr.start_review(self.order, self.u_cab)
        self.assertEqual(tr.allowed_actions(self.order, self.u_cab), ["forward", "return"])
        other_union = member(make_user("x", role="ym_union"), T.UNION, union_unit=make_union(self.district, "Бошқа"), can_sign=False)
        self.assertEqual(tr.allowed_actions(self.order, other_union), [])
