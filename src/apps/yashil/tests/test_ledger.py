"""Ombor ledger'i: qoldiq = harakatlar yig'indisi, qabulda ajratish, kirim, teskari operatsiya (TZ §9, §22.1; Q11–Q13, Q27, Q28, Q30, Q34)."""
from datetime import date, datetime, timezone as tz
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from apps.yashil.models import (
    Acceptance,
    Order,
    OrderLine,
    OrderState,
    ServiceAllocation,
    ServiceCapacity,
    StockMovement,
    Warehouse,
    YashilMembership,
)
from apps.yashil.services import ledger
from apps.yashil.services import transitions as tr
from apps.yashil.services.ledger import LedgerError
from apps.yashil.services.transitions import TransitionError
from apps.yashil.tests._common import (
    assign_forest, make_district, make_dm, make_forest, make_item, make_mahalla, make_region, make_union, make_user,
    member, route_union,
)

T = YashilMembership.MemberType
NOW = datetime(2027, 1, 11, 9, tzinfo=tz.utc)


class LedgerBase(TestCase):
    def setUp(self):
        cache.clear()
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.forest = make_forest()
        self.dm, p = make_dm(); p.service_regions.add(self.district.region)
        assign_forest(self.mahalla, self.forest)
        self.unit = make_union(self.district); route_union(self.mahalla, self.unit)
        self.ash = make_item("ASH", "Шумтол", "forest", "seedling", "tup")
        self.mul = make_item("MUL", "Мульча", "forest", "mulch", "kg")
        self.bio = make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        self.prt = make_item("PRT", "Ҳимоя", "dm", "protection_service", "daraxt", item_type="service")
        self.m_user = make_user("m", role="ym_mahalla"); self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla)
        self.f_user = make_user("f", role="tashkilot_hodimi", organization=self.forest)
        self.f_cab = member(self.f_user, T.SUPPLIER, organization=self.forest, can_sign=False)
        self.f_signer = member(make_user("fs", role="tashkilot_rahbari", organization=self.forest), T.SUPPLIER, organization=self.forest)
        self.d_user = make_user("d", role="tashkilot_hodimi", organization=self.dm)
        self.d_cab = member(self.d_user, T.SUPPLIER, organization=self.dm, can_sign=False)
        self.fw = ledger.default_warehouse(self.forest)
        self.dw = ledger.default_warehouse(self.dm)

    def order(self, lines, route="forest", org=None, number="YM-2027-000001"):
        org = org or (self.forest if route == "forest" else self.dm)
        o = Order.objects.create(mahalla=self.mahalla, route=route, supplier_org=org, union_unit=self.unit,
                                 created_by_membership=self.m_cab, title="Т", address="A", number=number,
                                 state=OrderState.SUPPLIER_REVIEW, lat=Decimal("41.3"), lon=Decimal("69.2"), area_ha=Decimal("1"))
        for item, qty in lines:
            OrderLine.objects.create(order=o, catalog_item=item, qty=Decimal(qty))
        return o

    def accept(self, order, cabinet):
        with patch("django.utils.timezone.now", return_value=NOW):
            return tr.accept(order, cabinet, executor_name="Иброҳимов")

    def opening(self, wh, item, qty, cabinet=None):
        return ledger.post_opening(wh, item, Decimal(qty), cabinet or (self.f_cab if wh == self.fw else self.d_cab),
                                   doc_number="ИНВ-1", doc_date=date(2026, 12, 31))


class WarehouseAndMovementsTest(LedgerBase):
    def test_default_warehouse_is_created_once_per_organization(self):
        again = ledger.default_warehouse(self.forest)
        self.assertEqual(again.pk, self.fw.pk)
        self.assertTrue(again.is_default)
        self.assertEqual(Warehouse.objects.filter(organization=self.forest).count(), 1)

    def test_q28_opening_and_receipts_sum_into_balance_and_history_is_kept(self):
        self.opening(self.fw, self.ash, "100")
        ledger.post_receipt(self.fw, self.ash, Decimal("150"), self.f_cab, doc_number="К-1", doc_date=date(2027, 1, 5))
        ledger.post_receipt(self.fw, self.ash, Decimal("25.5"), self.f_cab, doc_number="К-2", doc_date=date(2027, 1, 6))
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("275.5"))
        kinds = list(StockMovement.objects.filter(warehouse=self.fw).order_by("created_at").values_list("kind", flat=True))
        self.assertEqual(kinds, ["opening", "receipt", "receipt"])
        self.assertEqual(ledger.balance(self.fw, self.mul), Decimal("0"))

    def test_opening_is_a_single_documented_movement_per_item(self):
        self.opening(self.fw, self.ash, "100")
        with self.assertRaises(LedgerError) as cm:
            self.opening(self.fw, self.ash, "5")
        self.assertEqual(cm.exception.code, "opening_exists")
        self.opening(self.fw, self.mul, "40")  # boshqa pozitsiya — mumkin

    def test_receipt_validation_and_duplicate_doc_number_warning(self):
        with self.assertRaises(LedgerError) as cm:
            ledger.post_receipt(self.fw, self.ash, Decimal("0"), self.f_cab, doc_number="К-1", doc_date=date(2027, 1, 5))
        self.assertEqual(cm.exception.code, "invalid_qty")
        with self.assertRaises(LedgerError) as cm:
            ledger.post_receipt(self.fw, self.bio, Decimal("5"), self.f_cab, doc_number="К-1", doc_date=date(2027, 1, 5))
        self.assertEqual(cm.exception.code, "item_supplier_mismatch")
        with self.assertRaises(LedgerError) as cm:
            ledger.post_receipt(self.fw, self.ash, Decimal("5"), self.m_cab, doc_number="К-1", doc_date=date(2027, 1, 5))
        self.assertEqual(cm.exception.status, 403)
        _, warnings = ledger.post_receipt(self.fw, self.ash, Decimal("5"), self.f_cab, doc_number="К-1", doc_date=date(2027, 1, 5))
        self.assertEqual(warnings, [])
        _, warnings = ledger.post_receipt(self.fw, self.ash, Decimal("5"), self.f_cab, doc_number="К-1", doc_date=date(2027, 1, 6))
        self.assertEqual([w["code"] for w in warnings], ["doc_number_duplicate"])
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("10"))

    def test_reversal_is_requested_by_clerk_and_posted_only_after_signer_approval(self):
        self.opening(self.fw, self.ash, "100")
        receipt, _ = ledger.post_receipt(self.fw, self.ash, Decimal("50"), self.f_cab, doc_number="К-9", doc_date=date(2027, 1, 5))
        rev = ledger.request_reversal(receipt, self.f_cab, note="Хато киритилган")
        self.assertEqual((rev.kind, rev.status, rev.qty), ("reversal", "pending_approval", Decimal("-50")))
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("150"))
        with self.assertRaises(LedgerError) as cm:
            ledger.approve_reversal(rev, self.f_cab)
        self.assertEqual(cm.exception.code, "cannot_sign")
        with self.assertRaises(LedgerError) as cm:
            ledger.request_reversal(receipt, self.f_cab, note="Иккинчи марта")
        self.assertEqual(cm.exception.code, "reversal_pending")
        ledger.approve_reversal(rev, self.f_signer)
        rev.refresh_from_db()
        self.assertEqual((rev.status, rev.approved_by_id), ("posted", self.f_signer.user_id))
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("100"))
        with self.assertRaises(LedgerError) as cm:
            ledger.request_reversal(receipt, self.f_cab, note="Яна")
        self.assertEqual(cm.exception.code, "already_reversed")

    def test_rejected_reversal_leaves_balance_and_allocation_is_not_reversible(self):
        self.opening(self.fw, self.ash, "100")
        receipt, _ = ledger.post_receipt(self.fw, self.ash, Decimal("50"), self.f_cab, doc_number="К-9", doc_date=date(2027, 1, 5))
        rev = ledger.request_reversal(receipt, self.f_cab, note="x")
        ledger.reject_reversal(rev, self.f_signer, note="Асос йўқ")
        rev.refresh_from_db()
        self.assertEqual(rev.status, "rejected")
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("150"))
        self.accept(self.order([(self.ash, "60")]), self.f_cab)
        alloc = StockMovement.objects.get(kind="allocate")
        with self.assertRaises(LedgerError) as cm:
            ledger.request_reversal(alloc, self.f_cab, note="x")
        self.assertEqual(cm.exception.code, "not_reversible")


class AcceptAllocationTest(LedgerBase):
    def test_q11_accept_allocates_each_line_once_and_balance_drops(self):
        self.opening(self.fw, self.ash, "100")
        order = self.order([(self.ash, "60")])
        self.accept(order, self.f_cab)
        self.assertEqual(order.state, OrderState.EXECUTION)
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("40"))
        acc = Acceptance.objects.get(order=order)
        self.assertEqual((acc.warehouse_id, acc.accepted_on, acc.delivery_due), (self.fw.pk, date(2027, 1, 11), date(2027, 1, 25)))
        allocs = StockMovement.objects.filter(kind="allocate", acceptance=acc)
        self.assertEqual(list(allocs.values_list("qty", flat=True)), [Decimal("-60")])
        self.assertEqual(acc.result["lines"][0]["shortage"], "0")
        self.assertEqual(order.events.get(action="accept").payload["stock"]["lines"][0]["balance_after"], "40")

    def test_q12_q27_forest_balance_goes_negative_and_shortage_is_reported(self):
        self.opening(self.fw, self.ash, "100")
        self.accept(self.order([(self.ash, "60")], number="YM-2027-000001"), self.f_cab)
        o2 = self.order([(self.ash, "50")], number="YM-2027-000002")
        self.accept(o2, self.f_cab)
        self.assertEqual(o2.state, OrderState.EXECUTION)
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("-10"))
        row = next(r for r in ledger.warehouse_summary(self.forest) if r["code"] == "ASH")
        self.assertEqual((row["balance"], row["shortage"], row["allocated"]), ("-10", "10", "110"))
        o3 = self.order([(self.mul, "300")], number="YM-2027-000003")  # Q27: nol qoldiq
        self.accept(o3, self.f_cab)
        self.assertEqual(ledger.balance(self.fw, self.mul), Decimal("-300"))
        self.assertEqual(Acceptance.objects.get(order=o3).result["lines"][0]["shortage"], "300")

    def test_q12_q30_q34_dm_rejects_insufficient_stock_atomically(self):
        self.opening(self.dw, self.bio, "100")
        self.accept(self.order([(self.bio, "60")], route="dm", number="YM-2027-000001"), self.d_cab)
        o2 = self.order([(self.bio, "50"), (self.prt, "5")], route="dm", number="YM-2027-000002")
        with self.assertRaises(TransitionError) as cm:
            self.accept(o2, self.d_cab)
        exc = cm.exception
        self.assertEqual((exc.code, exc.status), ("stock_insufficient", 422))
        self.assertEqual(
            [(l["code"], l["need"], l["available"]) for l in exc.extra["lines"]],
            [("BIO", "50", "40"), ("PRT", "5", "0")],
        )
        o2.refresh_from_db()
        self.assertEqual(o2.state, OrderState.SUPPLIER_REVIEW)
        self.assertFalse(Acceptance.objects.filter(order=o2).exists())
        self.assertEqual(StockMovement.objects.filter(kind="allocate").count(), 1)
        self.assertEqual(ledger.balance(self.dw, self.bio), Decimal("40"))
        # DM kirim kiritib qayta qabul qiladi (Q30)
        ledger.post_receipt(self.dw, self.bio, Decimal("10"), self.d_cab, doc_number="К-1", doc_date=date(2027, 1, 10))
        with patch("django.utils.timezone.now", return_value=NOW):
            ServiceCapacity.objects.create(organization=self.dm, catalog_item=self.prt, period="2027-01", capacity=Decimal("5"))
        self.accept(o2, self.d_cab)
        self.assertEqual(ledger.balance(self.dw, self.bio), Decimal("0"))
        self.assertEqual(ServiceAllocation.objects.get(order_line__order=o2).qty, Decimal("5"))

    def test_dm_service_capacity_is_consumed_per_month(self):
        ServiceCapacity.objects.create(organization=self.dm, catalog_item=self.prt, period="2027-01", capacity=Decimal("100"))
        self.accept(self.order([(self.prt, "60")], route="dm", number="YM-2027-000001"), self.d_cab)
        self.assertEqual(ledger.capacity_available(self.dm, self.prt, "2027-01"), Decimal("40"))
        o2 = self.order([(self.prt, "50")], route="dm", number="YM-2027-000002")
        with self.assertRaises(TransitionError) as cm:
            self.accept(o2, self.d_cab)
        self.assertEqual(cm.exception.extra["lines"][0]["available"], "40")
        self.assertEqual(ledger.capacity_available(self.dm, self.prt, "2027-02"), Decimal("0"))

    def test_q13_repeat_accept_does_not_allocate_twice(self):
        self.opening(self.fw, self.ash, "100")
        order = self.order([(self.ash, "60")])
        self.accept(order, self.f_cab)
        with self.assertRaises(TransitionError):
            self.accept(order, self.f_cab)
        with self.assertRaises(LedgerError) as cm:
            ledger.allocate_for_acceptance(order, self.f_cab, accepted_on=date(2027, 1, 11), delivery_due=date(2027, 1, 25), executor_name="X")
        self.assertEqual((cm.exception.code, cm.exception.status), ("acceptance_exists", 409))
        self.assertEqual(StockMovement.objects.filter(kind="allocate").count(), 1)
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("40"))

    def test_release_restores_balance_only_for_given_quantity(self):
        self.opening(self.fw, self.ash, "100")
        order = self.order([(self.ash, "60")])
        self.accept(order, self.f_cab)
        line = order.lines.get()
        mv = ledger.release_for_cancel(line, Decimal("20"), cabinet=self.f_cab, note="Қисман бекор")
        self.assertEqual((mv.kind, mv.qty, mv.acceptance_id), ("release", Decimal("20"), order.acceptance.pk))
        self.assertEqual(ledger.balance(self.fw, self.ash), Decimal("60"))
        row = next(r for r in ledger.warehouse_summary(self.forest) if r["code"] == "ASH")
        self.assertEqual((row["allocated"], row["released"], row["balance"]), ("60", "20", "60"))

    def test_summary_lists_catalog_items_with_zero_rows_and_observer_cannot_post(self):
        rows = ledger.warehouse_summary(self.forest)
        self.assertEqual([r["code"] for r in rows], ["ASH", "MUL"])
        self.assertEqual(rows[0]["balance"], "0")
        observer = member(make_user("o", role="ym_observer"), T.OBSERVER, can_prepare=False, can_sign=False)
        with self.assertRaises(LedgerError) as cm:
            ledger.post_receipt(self.fw, self.ash, Decimal("5"), observer, doc_number="К", doc_date=date(2027, 1, 5))
        self.assertEqual(cm.exception.status, 403)
