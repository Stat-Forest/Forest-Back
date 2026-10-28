"""Buyurtma, versiya, hujjat va imzo modellarining cheklovlari (TZ §20)."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.yashil.models import (
    Document, DocumentVersion, Order, OrderLine, OrderState, OrderVersion, ReviewSegment, Signature,
    YashilMembership,
)
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_item, make_mahalla, make_region, make_user, member,
)


class OrderModelTest(TestCase):
    def setUp(self):
        self.district = make_district(make_region())
        self.mahalla = make_mahalla(self.district)
        self.forest = make_forest()
        assign_forest(self.mahalla, self.forest)
        self.user = make_user("m", role="ym_mahalla")
        self.cab = member(self.user, YashilMembership.MemberType.MAHALLA, mahalla=self.mahalla)
        self.ash = make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup")

    def new_order(self, **kw):
        return Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest,
                                    created_by_membership=self.cab, title="Test", **kw)

    def test_draft_has_no_number_and_version_one(self):
        o = self.new_order()
        self.assertEqual(o.state, OrderState.DRAFT)
        self.assertIsNone(o.number)
        self.assertEqual(o.version_no, 1)

    def test_same_catalog_item_twice_is_rejected(self):
        o = self.new_order()
        OrderLine.objects.create(order=o, catalog_item=self.ash, qty=Decimal("10"))
        with self.assertRaises((IntegrityError, ValidationError)):
            OrderLine.objects.create(order=o, catalog_item=self.ash, qty=Decimal("5"))

    def test_version_snapshot_is_unique_per_order_version(self):
        o = self.new_order()
        OrderVersion.objects.create(order=o, version_no=1, snapshot={"a": 1}, submitted_by=self.user)
        with self.assertRaises(IntegrityError):
            OrderVersion.objects.create(order=o, version_no=1, snapshot={"a": 2}, submitted_by=self.user)

    def test_open_review_segment_is_single(self):
        o = self.new_order()
        ReviewSegment.objects.create(order=o, started_on="2027-01-11")
        self.assertEqual(o.review_segments.filter(ended_on__isnull=True).count(), 1)
        self.assertEqual(o.review_segments_as_tuples(), [("2027-01-11", None)])

    def test_document_version_hash_and_qr_token_are_generated(self):
        o = self.new_order()
        doc = Document.objects.create(kind=Document.Kind.ORDER_FORM, order=o)
        v = DocumentVersion.objects.create(document=doc, version_no=1, template_version=1,
                                           content={"number": "YM-2027-000001"}, html="<p>x</p>")
        self.assertEqual(len(v.content_hash), 64)
        self.assertGreaterEqual(len(v.qr_token), 20)
        self.assertEqual(v.status, DocumentVersion.Status.UNSIGNED)
        v2 = DocumentVersion.objects.create(document=doc, version_no=2, template_version=1,
                                            content={"number": "YM-2027-000001"}, html="<p>x</p>")
        self.assertEqual(v.content_hash, v2.content_hash)
        self.assertNotEqual(v.qr_token, v2.qr_token)

    def test_one_signature_per_role_per_document_version(self):
        o = self.new_order()
        doc = Document.objects.create(kind=Document.Kind.ORDER_FORM, order=o)
        v = DocumentVersion.objects.create(document=doc, version_no=1, template_version=1, content={}, html="")
        Signature.objects.create(document_version=v, signer_user=self.user, signer_membership=self.cab,
                                 role=Signature.Role.MAHALLA, pkcs7="x", mode="challenge", is_valid=True)
        with self.assertRaises(IntegrityError):
            Signature.objects.create(document_version=v, signer_user=self.user, signer_membership=self.cab,
                                     role=Signature.Role.MAHALLA, pkcs7="y", mode="challenge", is_valid=True)
