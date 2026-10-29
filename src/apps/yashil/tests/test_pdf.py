"""PDF (TZ §13.3): buyurtmanoma va dalolatnoma PDF'i kirill shrift bilan, imzodan keyin qayta yaratiladi, yuklash havolasi."""
import re
from datetime import date, datetime, timezone as tz
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.yashil.models import ActAttachment, DocumentVersion, Order, OrderLine, OrderState, Signature, YashilMembership
from apps.yashil.services import acts as act_service
from apps.yashil.services import pdf as pdf_service
from apps.yashil.services import signing
from apps.yashil.services import transitions as tr
from apps.yashil.services.documents import build_order_form
from apps.yashil.tests._common import (
    BASE, assign_forest, auth, make_district, make_forest, make_item, make_mahalla, make_region, make_union, make_user,
    member, route_union,
)
from apps.yashil.tests._eimzo import FakeEimzo, fake_sign

T = YashilMembership.MemberType
NOW = datetime(2027, 1, 11, 9, tzinfo=tz.utc)
LATER = datetime(2027, 1, 15, 9, tzinfo=tz.utc)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
M_PINFL, S_PINFL = "31234567890123", "55555555555555"


def page_count(data: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", data))


def dump(name: str, data: bytes) -> None:
    """Ko'z bilan tekshirish uchun: YASHIL_PDF_DUMP=<papka> berilsa PDF shu yerga yoziladi."""
    import os

    folder = os.environ.get("YASHIL_PDF_DUMP")
    if folder:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, name), "wb") as f:
            f.write(data)


class PdfTest(APITestCase):
    def setUp(self):
        cache.clear()
        d = make_district(make_region())
        self.mahalla = make_mahalla(d)
        self.other = make_mahalla(d, "Бошқа маҳалла")
        self.forest = make_forest("Намуна ўрмон хўжалиги")
        assign_forest(self.mahalla, self.forest)
        self.unit = make_union(d); route_union(self.mahalla, self.unit)
        self.ash = make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup")
        self.m_user = make_user("m", role="ym_mahalla", pinfl=M_PINFL, father_name="Алиевич")
        self.m_cab = member(self.m_user, T.MAHALLA, mahalla=self.mahalla, position_title="Маҳалла раиси")
        self.s_user = make_user("s", role="tashkilot_rahbari", organization=self.forest, pinfl=S_PINFL)
        self.s_cab = member(self.s_user, T.SUPPLIER, organization=self.forest, position_title="Директор")
        self.x_user = make_user("x", role="ym_mahalla"); self.x_cab = member(self.x_user, T.MAHALLA, mahalla=self.other)
        self.order = Order.objects.create(mahalla=self.mahalla, route="forest", supplier_org=self.forest, union_unit=self.unit,
                                          created_by_membership=self.m_cab, title="Боғистонга кўчат", address="Боғистон, 5-уй",
                                          number="YM-2027-000001", state=OrderState.DRAFT, lat=Decimal("41.311081"), lon=Decimal("69.240562"),
                                          area_ha=Decimal("0.5"), extra_info="Сув манбаи — ариқ")
        for i in range(30):  # uzun jadval — ikkinchi sahifada sarlavha takrorlanadi (TZ §11.2)
            item = self.ash if i == 0 else make_item(f"IT{i}", f"Кўчат тури {i}", "forest", "seedling", "tup")
            OrderLine.objects.create(order=self.order, catalog_item=item, qty=Decimal(100 + i), position=i)
        self.request_factory = None

    def test_order_form_pdf_has_cyrillic_font_qr_and_multiple_pages(self):
        v = build_order_form(self.order, self.m_cab)
        data = pdf_service.render_pdf(v)
        dump("order_form.pdf", data)
        self.assertTrue(data.startswith(b"%PDF-1."))
        self.assertIn(b"%%EOF", data[-64:])
        self.assertIn(b"DejaVuSans", data)
        self.assertGreaterEqual(page_count(data), 2)
        self.assertGreater(len(data), 5000)

    def test_attach_pdf_stores_protected_file_and_signature_invalidates_it(self):
        v = build_order_form(self.order, self.m_cab)
        f = pdf_service.ensure_pdf(v)
        self.assertTrue(f.name.startswith("documents/yashil/pdf/"))
        self.assertIn("YM-2027-000001-v1", f.name)
        first_name = f.name
        self.assertEqual(pdf_service.ensure_pdf(v).name, first_name)  # qayta yaratilmaydi
        with patch.object(signing, "eimzo_api", FakeEimzo(pinfl=M_PINFL)):
            from rest_framework.test import APIRequestFactory

            req = APIRequestFactory().post("/x")
            task = signing.prepare_signing(v, self.m_user, self.m_cab, Signature.Role.MAHALLA, req)
            signing.verify_and_store(v, self.m_user, self.m_cab, Signature.Role.MAHALLA, fake_sign(task["sign_text"]), task["nonce"], req)
        v.refresh_from_db()
        self.assertFalse(bool(v.pdf_file))
        signed = pdf_service.ensure_pdf(v)
        self.assertNotEqual(signed.name, first_name)
        self.assertEqual(v.status, "signed")

    def test_act_pdf_renders_with_two_signature_rows(self):
        Order.objects.filter(pk=self.order.pk).update(state=OrderState.SUPPLIER_REVIEW)
        self.order.refresh_from_db()
        with patch("django.utils.timezone.now", return_value=NOW):
            tr.accept(self.order, self.s_cab, executor_name="Иброҳимов")
        with patch("django.utils.timezone.now", return_value=LATER):
            act = act_service.create_act(self.order, self.s_cab, delivery_date=date(2027, 1, 14),
                                         lines=[{"order_line": self.order.lines.first(), "qty": Decimal("10")}], responsible="И.", note="Етказилди")
        ActAttachment.objects.create(act=act, version_no=1, file=SimpleUploadedFile("f.png", PNG, content_type="image/png"),
                                     original_name="f.png", size=len(PNG), kind="photo", uploaded_by=self.s_user)
        from rest_framework.test import APIRequestFactory

        req = APIRequestFactory().post("/x")
        with patch.object(signing, "eimzo_api", FakeEimzo(pinfl=S_PINFL)), patch("django.utils.timezone.now", return_value=LATER):
            task = act_service.sign_task(act, self.s_cab, req)
            act_service.sign(act, self.s_cab, pkcs7=fake_sign(task["sign_text"]), nonce=task["nonce"], request=req)
        act.refresh_from_db()
        dv = act.current_version.document_version
        dv.refresh_from_db()
        data = pdf_service.render_pdf(dv)
        dump("act.pdf", data)
        self.assertTrue(data.startswith(b"%PDF-1."))
        self.assertIn(b"DejaVuSans", data)
        self.assertEqual(page_count(data), 1)

    def test_pdf_endpoint_returns_signed_relative_url_within_scope(self):
        v = build_order_form(self.order, self.m_cab)
        auth(self.client, self.m_user, self.m_cab)
        res = self.client.get(f"{BASE}/documents/{v.pk}/pdf/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data["url"].startswith("/media/documents/yashil/pdf/"))
        self.assertIn("?t=", res.data["url"])
        self.assertEqual(res.data["filename"], "YM-2027-000001-v1.pdf")
        self.assertGreater(res.data["size"], 1000)
        v.refresh_from_db()
        self.assertTrue(bool(v.pdf_file))
        self.client.credentials()
        auth(self.client, self.x_user, self.x_cab)
        self.assertEqual(self.client.get(f"{BASE}/documents/{v.pk}/pdf/").status_code, 404)
