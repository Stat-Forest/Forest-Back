"""Hujjat tili (D-28, C bosqich): hujjat yaratilgan paytdagi tilda — uz lotin, ru rus; eski (tilsiz) hujjat kirillda qoladi."""
import html as html_lib
import re
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import translation

from apps.yashil.models import DocumentVersion, Order, OrderLine, YashilMembership
from apps.yashil.services import cancel as cancel_service
from apps.yashil.services import lang
from apps.yashil.services import pdf as pdf_service
from apps.yashil.services.documents import build_order_form, render_html
from apps.yashil.services.lang_ru import DOC_RU, RU
from apps.yashil.tests.test_cancel import LATER, CancelBase
from apps.yashil.tests._common import (
    assign_forest, make_district, make_forest, make_item, make_mahalla, make_region, make_user, member,
)

CYR = re.compile(r"[Ѐ-ӿ]")
TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "yashil"
DOC_TAG = re.compile(r'\{%\s*d\s+"([^"]*)"[^%]*%\}')


def story_text(flowables) -> str:
    """PDF story'dagi barcha Paragraph matnlari (jadval va KeepTogether ichidagilari ham)."""
    out = []

    def walk(f):
        if isinstance(f, (list, tuple)):
            for x in f:
                walk(x)
        elif hasattr(f, "_cellvalues"):
            walk(f._cellvalues)
        elif hasattr(f, "_content"):
            walk(f._content)
        elif hasattr(f, "text") and isinstance(f.text, str):
            out.append(f.text)

    walk(flowables)
    return "\n".join(out)


def pdf_story(build, version) -> str:
    pdf_service._register_fonts()
    return story_text(build(version))


class DocTextTest(SimpleTestCase):
    def test_legacy_uz_ru(self):
        self.assertEqual(lang.doc_text("Рақами", None), "Рақами")
        self.assertEqual(lang.doc_text("Рақами", "uz"), "Raqami")
        self.assertEqual(lang.doc_text("Рақами", "ru"), "Номер")

    def test_values_are_inserted_as_is(self):
        self.assertEqual(lang.doc_text("Объект номи: {0}.", "ru", "Кўчат {1}"), "Наименование объекта: Кўчат {1}.")
        self.assertEqual(lang.doc_text("Объект номи: {0}.", "uz", "Кўчат"), "Obyekt nomi: Кўчат.")
        self.assertEqual(lang.doc_text("{0}га", None, "ДМ"), "ДМга")

    def test_document_phrases_do_not_leak_into_messages(self):
        # «{0}га» kabi qisqa shablonlar umumiy xabar o'girishga ta'sir qilmasin
        self.assertEqual(lang.tr("Номаълум хўжаликка", "ru"), "Номаълум хўжаликка")

    def test_hard_sign_before_ye(self):
        self.assertEqual(lang.to_lat("Объект"), "Obyekt")
        self.assertEqual(lang.to_lat("маъмур"), "ma'mur")


class DocumentLangBase(TestCase):
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
                                          water_source="ариқ", number="YM-2027-000001")
        OrderLine.objects.create(order=self.order, catalog_item=make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup"), qty=Decimal("300"))

    def build(self, code):
        with translation.override(code):
            return build_order_form(self.order, self.cab)


class OrderFormLangTest(DocumentLangBase):
    USER_TEXT = ("Кўчат", "Боғистон, 5-уй", "ариқ", "Алиевич", "Маҳалла раиси")

    def system_cyrillic(self, text: str) -> list[str]:
        for user in self.USER_TEXT:
            text = text.replace(user, "")
        return CYR.findall(text)

    def test_uz_document_is_latin(self):
        v = self.build("uz")
        c = v.content
        self.assertEqual((c["lang"], v.template_version, c["template_version"]), ("uz", 2, 2))
        self.assertEqual(c["supplier_name"], "Namuna o'rmon xo'jaligi")
        self.assertEqual(c["subject_phrase"], "mahsulotlarni yetkazib berish")
        self.assertEqual((c["lines"][0]["name"], c["lines"][0]["unit"]), ("Shumtol ko'chati", "tup"))
        self.assertEqual(c["extra_info"], "Suv manbai: ариқ")
        self.assertEqual(c["attachments_text"], "Yo'q")
        page = html_lib.unescape(v.html)
        self.assertIn('lang="uz"', page)
        self.assertIn("PF-206-son Farmoniga asosan", page)
        self.assertIn("Buyurtmanoma", page)
        self.assertIn("Imzolanmagan", page)
        self.assertEqual(self.system_cyrillic(page), [])
        pdf_text = html_lib.unescape(pdf_story(pdf_service._order_form_story, v))
        self.assertIn("BUYURTMANOMA", pdf_text)
        self.assertIn("IMZOLANMAGAN NUSXA", pdf_text)
        self.assertEqual(self.system_cyrillic(pdf_text), [])
        self.assertTrue(pdf_service.render_pdf(v).startswith(b"%PDF-1."))

    def test_ru_document_is_russian(self):
        v = self.build("ru")
        c = v.content
        self.assertEqual(c["lang"], "ru")
        self.assertEqual(c["subject_phrase"], "поставку продукции")
        self.assertEqual((c["lines"][0]["name"], c["lines"][0]["unit"]), ("Shumtol ko'chati", "шт."))
        self.assertEqual(c["extra_info"], "Источник воды: ариқ")
        self.assertEqual(c["supplier_name"], "Намуна ўрмон хўжалиги")  # ma'lumotnoma nomi o'zgarmaydi
        page = html_lib.unescape(v.html)
        self.assertIn('lang="ru"', page)
        self.assertIn("Указа Президента Республики Узбекистан", page)
        self.assertIn("Не подписан", page)
        self.assertNotIn("Буюртманома", page)
        self.assertNotIn("Имзо", page)
        pdf_text = html_lib.unescape(pdf_story(pdf_service._order_form_story, v))
        self.assertIn("ЗАЯВКА", pdf_text)
        self.assertNotIn("ИМЗОЛАНМАГАН", pdf_text)
        self.assertNotIn("Буюртма берувчи", pdf_text)
        self.assertTrue(pdf_service.render_pdf(v).startswith(b"%PDF-1."))

    def test_legacy_content_without_lang_stays_cyrillic(self):
        v = self.build("uz")
        legacy = {k: val for k, val in v.content.items() if k != "lang"}
        DocumentVersion.objects.filter(pk=v.pk).update(content=legacy)
        v.refresh_from_db()
        page = html_lib.unescape(render_html(v))
        self.assertIn('lang="uz"', page)
        self.assertIn("Ўзбекистон Республикаси Президентининг 2026 йил 23 сентябрдаги ПФ-206-сон Фармонига асосан", page)
        self.assertIn("Буюртманома", page)
        self.assertIn("Имзоланмаган", page)
        pdf_text = pdf_story(pdf_service._order_form_story, v)
        self.assertIn("БУЮРТМАНОМА", pdf_text)
        self.assertIn("ИМЗОЛАНМАГАН НУСХА", pdf_text)


class DocumentCatalogTest(SimpleTestCase):
    def test_every_template_phrase_has_russian(self):
        missing = []
        for path in sorted(TEMPLATES.glob("*.html")):
            text = path.read_text(encoding="utf-8")
            for phrase in DOC_TAG.findall(text):
                if phrase not in DOC_RU and phrase not in RU:
                    missing.append(f"{path.name}: {phrase!r}")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_templates_have_no_untranslated_cyrillic(self):
        bad = []
        for path in sorted(TEMPLATES.glob("*.html")):
            text = DOC_TAG.sub("", path.read_text(encoding="utf-8"))
            bad += [f"{path.name}: {line.strip()[:80]}" for line in text.splitlines() if CYR.search(line)]
        self.assertEqual(bad, [], "\n".join(bad))

    def test_placeholders_match(self):
        ph = re.compile(r"\{\d+\}")
        self.assertEqual([k for k, v in DOC_RU.items() if sorted(ph.findall(k)) != sorted(ph.findall(v))], [])


class ActAndCancellationLangTest(CancelBase):
    def test_act_and_cancellation_follow_creation_language(self):
        self.accept()
        with translation.override("ru"):
            act = self.approved_act("40")
        dv = act.current_version.document_version
        dv.refresh_from_db()
        c = dv.content
        self.assertEqual((c["lang"], dv.template_version), ("ru", 2))
        self.assertEqual((c["lines"][0]["name"], c["lines"][0]["unit"]), ("Shumtol", "шт."))
        self.assertIn("точка", c["object_text"])
        page = html_lib.unescape(dv.html)
        self.assertIn("АКТ ПРИЁМА-ПЕРЕДАЧИ", page)
        self.assertIn("Подписан обеими сторонами", page)
        pdf_text = pdf_story(pdf_service._act_story, dv)
        self.assertIn("АКТ ПРИЁМА-ПЕРЕДАЧИ", pdf_text)
        self.assertIn("Подписан полностью", pdf_text)
        self.assertNotIn("Етказиб берувчи", pdf_text)

        with translation.override("uz"):
            req = cancel_service.request_cancel(self.order, self.m_cab, lines=[], reason="Ҳудуд ўзгарди")
            cancel_service.agree_cancel(req, self.s_cab)
            with patch("django.utils.timezone.now", return_value=LATER):
                cancel_service.approve_cancel(req, self.u_cab)
        cv = req.document.current_version
        c = cv.content
        self.assertEqual(c["lang"], "uz")
        self.assertEqual(c["result_label"], "Buyurtma bekor qilingan")
        self.assertTrue(c["requested_by"].startswith("Mahalla — "))
        self.assertEqual((c["lines"][0]["name"], c["lines"][0]["unit"]), ("Shumtol", "tup"))
        page = html_lib.unescape(cv.html)
        self.assertIn("BUYURTMANI BEKOR QILISH HUJJATI", page)
        self.assertIn("Ҳудуд ўзгарди", page)  # sabab — foydalanuvchi matni, o'zgarmaydi
        pdf_text = html_lib.unescape(pdf_story(pdf_service._cancellation_story, cv))
        self.assertIn("BUYURTMANI BEKOR QILISH HUJJATI", pdf_text)
        self.assertIn("Yakuniy holat", pdf_text)
