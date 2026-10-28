"""Buyurtmanoma hujjati: mazmun, HTML, hash, versiya, ochiq QR ko'rinishi (TZ §11, §13.2)."""
from decimal import Decimal

from django.test import TestCase

from apps.yashil.models import Document, DocumentVersion, Order, OrderLine, YashilMembership
from apps.yashil.services.documents import build_order_form, public_verify_payload
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_item, make_mahalla, make_region, make_user, member,
)


class OrderFormDocumentTest(TestCase):
    def setUp(self):
        d = make_district(make_region())
        self.mahalla = make_mahalla(d)
        self.forest = make_forest("Намуна ўрмон хўжалиги")
        assign_forest(self.mahalla, self.forest)
        self.user = make_user("m", role="ym_mahalla", father_name="Алиевич")
        self.cab = member(self.user, YashilMembership.MemberType.MAHALLA, mahalla=self.mahalla,
                          position_title="Маҳалла раиси", phone="+998901234567")
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest,
                                          created_by_membership=self.cab, title="Кўчат", address="Боғистон, 5-уй",
                                          lat=Decimal("41.311081"), lon=Decimal("69.240562"), area_ha=Decimal("0.5"),
                                          extra_info="Сув манбаи — ариқ", number="YM-2027-000001")
        OrderLine.objects.create(order=self.order, catalog_item=make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup"), qty=Decimal("300"))
        OrderLine.objects.create(order=self.order, catalog_item=make_item("MUL", "Мульча", "forest", "mulch", "kg"), qty=Decimal("1200"))

    def test_content_follows_tz_11_1_and_html_renders(self):
        v = build_order_form(self.order, self.cab)
        c = v.content
        self.assertEqual(c["number"], "YM-2027-000001")
        self.assertEqual(c["version_no"], 1)
        self.assertEqual(c["supplier_name"], "Намуна ўрмон хўжалиги")
        self.assertEqual(c["mahalla_name"], "Боғистон маҳалласи")
        self.assertEqual(c["point"], "41.311081, 69.240562")
        self.assertEqual(c["area_ha"], "0.5")
        self.assertEqual(c["subject_phrase"], "маҳсулотларни етказиб бериш")
        self.assertEqual([l["qty"] for l in c["lines"]], ["300", "1200"])
        self.assertIn("Алиевич", c["signer"]["full_name"])
        self.assertEqual(c["signer"]["position"], "Маҳалла раиси")
        self.assertIn("ПФ-206", v.html)
        self.assertIn("YM-2027-000001", v.html)
        self.assertIn("Имзоланмаган", v.html)
        self.assertEqual(v.status, DocumentVersion.Status.UNSIGNED)
        self.assertEqual(v.document.kind, Document.Kind.ORDER_FORM)
        self.assertEqual(v.document.number, "YM-2027-000001")

    def test_rebuild_supersedes_unsigned_previous_version(self):
        v1 = build_order_form(self.order, self.cab)
        v2 = build_order_form(self.order, self.cab)
        v1.refresh_from_db()
        self.assertEqual((v1.version_no, v2.version_no), (1, 2))
        self.assertEqual(v1.status, DocumentVersion.Status.SUPERSEDED)
        self.assertEqual(v2.document_id, v1.document_id)
        self.assertEqual(self.order.documents.count(), 1)

    def test_mixed_phrase_for_goods_and_service(self):
        dm_item = make_item("PRT", "Ҳимоя", "dm", "protection_service", "daraxt", item_type="service")
        self.order.lines.all().delete()
        OrderLine.objects.create(order=self.order, catalog_item=dm_item, qty=Decimal("10"))
        self.order.route = "dm"; self.order.save()
        v = build_order_form(self.order, self.cab)
        self.assertEqual(v.content["subject_phrase"], "хизматларни кўрсатиш")

    def test_public_verify_payload_has_no_personal_data(self):
        v = build_order_form(self.order, self.cab)
        p = public_verify_payload(v)
        self.assertEqual(p["status"], "unsigned")
        self.assertEqual(p["number"], "YM-2027-000001")
        self.assertEqual(p["parties"]["mahalla"], "Боғистон маҳалласи")
        self.assertEqual(p["signatures"], [])
        flat = str(p)
        for secret in ("41.311", "+99890", "Алиевич", "Боғистон, 5-уй"):
            self.assertNotIn(secret, flat)
