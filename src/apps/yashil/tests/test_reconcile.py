"""Tungi solishtirish (TZ §22.3): ajratish yaxlitligi, qabul ≤ buyurtma, yopiq buyurtma to'liqligi, manfiy qoldiq xabari."""
from datetime import date, datetime, timezone as tz
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from apps.yashil.models import Act, ActLine, Order, OrderLine, OrderState, ReconcileIssue, StockMovement, YashilMembership, YashilNotification
from apps.yashil.services import ledger
from apps.yashil.services import transitions as tr
from apps.yashil.tasks import reconcile
from apps.yashil.tests._common import (
    assign_forest, make_district, make_dm, make_forest, make_item, make_mahalla, make_region, make_union, make_user, member,
    route_union,
)

T = YashilMembership.MemberType
NOW = datetime(2027, 1, 11, 9, tzinfo=tz.utc)


class ReconcileTest(TestCase):
    def setUp(self):
        cache.clear()
        d = make_district(make_region())
        self.mahalla = make_mahalla(d)
        self.forest = make_forest(); assign_forest(self.mahalla, self.forest)
        self.dm, p = make_dm(); p.service_regions.add(d.region)
        self.unit = make_union(d); route_union(self.mahalla, self.unit)
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        self.bio = make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        self.m_cab = member(make_user("m", role="ym_mahalla"), T.MAHALLA, mahalla=self.mahalla)
        self.s_user = make_user("s", role="tashkilot_rahbari", organization=self.forest)
        self.s_cab = member(self.s_user, T.SUPPLIER, organization=self.forest)
        self.o_user = make_user("o", role="ym_observer"); member(self.o_user, T.OBSERVER, can_prepare=False, can_sign=False)
        self.wh = ledger.default_warehouse(self.forest)

    def order(self, qty="100", number="YM-2027-000001"):
        o = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest, union_unit=self.unit,
                                 created_by_membership=self.m_cab, title="T", address="A", number=number, state=OrderState.SUPPLIER_REVIEW)
        OrderLine.objects.create(order=o, catalog_item=self.ash, qty=Decimal(qty))
        with patch("django.utils.timezone.now", return_value=NOW):
            tr.accept(o, self.s_cab, executor_name="И.")
        return o

    def kinds(self, user):
        return list(YashilNotification.objects.filter(recipient_user=user).order_by("id").values_list("kind", flat=True))

    def test_clean_state_has_no_issues_but_negative_forest_balance_notifies_once(self):
        self.order()  # qoldiq −100
        result = reconcile()
        self.assertEqual(result["issues_new"], 0)
        self.assertEqual(self.kinds(self.s_user), ["stock_negative"])
        self.assertEqual(self.kinds(self.o_user), [])
        reconcile()
        self.assertEqual(self.kinds(self.s_user), ["stock_negative"])  # takrorlanmaydi
        ledger.post_receipt(self.wh, self.ash, Decimal("150"), self.s_cab, doc_number="К", doc_date=date(2027, 1, 5))
        reconcile()
        self.assertFalse(ReconcileIssue.objects.filter(kind="stock_negative", resolved_at__isnull=True).exists())
        ledger.post_opening(ledger.default_warehouse(self.dm), self.bio, Decimal("1"), member(make_user("d", organization=self.dm), T.SUPPLIER, organization=self.dm),
                            doc_number="x", doc_date=date(2026, 12, 31))
        self.order(qty="200", number="YM-2027-000002")  # yana manfiy → yangi xabar
        reconcile()
        self.assertEqual(self.kinds(self.s_user), ["stock_negative", "stock_negative"])

    def test_missing_and_duplicate_allocation_are_reported_and_resolved(self):
        o = self.order()
        alloc = StockMovement.objects.get(kind="allocate")
        StockMovement.objects.filter(pk=alloc.pk).update(status="rejected")  # go'yo yo'qolgan
        result = reconcile()
        self.assertEqual(result["issues_new"], 1)
        issue = ReconcileIssue.objects.get(kind="allocation_missing")
        self.assertEqual((issue.order_id, issue.resolved_at), (o.id, None))
        self.assertEqual(self.kinds(self.o_user), ["reconcile_issue"])
        reconcile()
        self.assertEqual(ReconcileIssue.objects.count(), 1)  # bir xil muammo ikki marta yozilmaydi
        StockMovement.objects.filter(pk=alloc.pk).update(status="posted")
        reconcile()
        issue.refresh_from_db()
        self.assertIsNotNone(issue.resolved_at)

    def test_accepted_exceeds_and_closed_incomplete(self):
        o = self.order()
        line = o.lines.get()
        act = Act.objects.create(order=o, index=1, number="YM-2027-000001/A1", status=Act.Status.APPROVED)
        from apps.yashil.models import ActVersion

        v = ActVersion.objects.create(act=act, version_no=1, delivery_date=date(2027, 1, 12))
        act.current_version = v; act.save()
        ActLine.objects.create(act_version=v, order_line=line, qty=Decimal("120"))
        Order.objects.filter(pk=o.pk).update(state=OrderState.CLOSED)
        reconcile()
        self.assertEqual(set(ReconcileIssue.objects.exclude(kind="stock_negative").values_list("kind", flat=True)), {"accepted_exceeds"})
        ActLine.objects.filter(act_version=v).update(qty=Decimal("80"))
        reconcile()
        kinds = set(ReconcileIssue.objects.filter(resolved_at__isnull=True).exclude(kind="stock_negative").values_list("kind", flat=True))
        self.assertEqual(kinds, {"closed_incomplete"})
