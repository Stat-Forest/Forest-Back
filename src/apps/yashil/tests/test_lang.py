"""Modul xabarlari tili (D-28): uz — lotin, ru — ruscha; so'rov tili Accept-Language orqali."""
import ast
import re
from pathlib import Path

from django.test import SimpleTestCase
from django.utils import translation

from apps.yashil.models import YashilNotification
from apps.yashil.services import lang
from apps.yashil.services.lang_ru import DOC_RU, RU
from apps.yashil.tests._common import BASE
from apps.yashil.tests.test_order_api import OrderApiBase

APP = Path(__file__).resolve().parents[1]
CYR = re.compile(r"[Ѐ-ӿ]")


class ToLatTest(SimpleTestCase):
    def test_uzbek_letters(self):
        self.assertEqual(lang.to_lat("Буюртма топилмади ёки очиш ҳуқуқи йўқ"), "Buyurtma topilmadi yoki ochish huquqi yo'q")
        self.assertEqual(lang.to_lat("Ўрмон хўжалиги"), "O'rmon xo'jaligi")
        self.assertEqual(lang.to_lat("Ғалла, ғўза"), "G'alla, g'o'za")
        self.assertEqual(lang.to_lat("Шумтол кўчати"), "Shumtol ko'chati")

    def test_ye_at_word_start_and_after_vowel(self):
        self.assertEqual(lang.to_lat("Етказиб берувчи"), "Yetkazib beruvchi")
        self.assertEqual(lang.to_lat("оила ер"), "oila yer")
        self.assertEqual(lang.to_lat("мае"), "maye")

    def test_case_and_signs(self):
        self.assertEqual(lang.to_lat("ДМ"), "DM")
        self.assertEqual(lang.to_lat("ШАРТНОМА"), "SHARTNOMA")
        self.assertEqual(lang.to_lat("Шарт"), "Shart")
        self.assertEqual(lang.to_lat("маъмур"), "ma'mur")
        self.assertEqual(lang.to_lat("Фильтр"), "Filtr")
        self.assertEqual(lang.to_lat("YM-2026-000001 · 12.03"), "YM-2026-000001 · 12.03")


class TranslateTest(SimpleTestCase):
    def test_uz_is_latin(self):
        self.assertEqual(lang.tr("Буюртма бу ҳолатда юборилмайди", "uz"), "Buyurtma bu holatda yuborilmaydi")

    def test_ru_exact(self):
        self.assertEqual(lang.tr("Сифат", "ru"), "Качество")

    def test_ru_template_keeps_values(self):
        self.assertEqual(lang.tr("Буюртма YM-2026-000123 ижрога қабул қилинди", "ru"), "Заявка YM-2026-000123 принята к исполнению")

    def test_ru_values_are_translated_or_latin(self):
        # birlik katalogdan, nom lotinda
        self.assertEqual(lang.tr("Шумтол кўчати: 300 туп учун кўпи билан 30 кг (0.1 кг/туп)", "ru"),
                         "Shumtol ko'chati: на 300 шт. не более 30 кг (0.1 кг/шт.)")

    def test_ru_nested_template(self):
        self.assertEqual(lang.tr("Буюртма YM-1 тузатишга қайтарилди (етказиб берувчи)", "ru"),
                         "Заявка YM-1 возвращена на исправление (поставщик)")

    def test_ru_unknown_text_unchanged(self):
        self.assertEqual(lang.tr("Это поле обязательно.", "ru"), "Это поле обязательно.")

    def test_known_only_leaves_user_text(self):
        self.assertEqual(lang.tr_known("Кўчатлар куз фаслида керак", "uz"), "Кўчатлар куз фаслида керак")
        self.assertEqual(lang.tr_known("Охирги муддат 01.03.2027", "uz"), "Oxirgi muddat 01.03.2027")
        self.assertEqual(lang.tr_known("Охирги муддат 01.03.2027", "ru"), "Крайний срок 01.03.2027")

    def test_current_follows_activated_language(self):
        with translation.override("ru"):
            self.assertEqual(lang.current(), "ru")
        with translation.override("uz"):
            self.assertEqual(lang.current(), "uz")
        with translation.override("en"):
            self.assertEqual(lang.current(), "uz")


# Xabar emas: Excel ustun nomlari (foydalanuvchi faylidagi sarlavha bilan solishtiriladi) va qiymat so'zlari
NOT_MESSAGES = {
    "да", "фаол", "нет", "нофаол", "манба коди", "код", "вилоят коди", "туман коди", "маҳалла номи", "номи", "маҳалла коди",
    "маҳалла", "хўжалик", "ташкилот", "амал бошланиши", "амал тугаши", "уюшма бўлинмаси", "уюшма", "сана", "тури",
    "каталог коди", "позиция коди", "миқдор", "қолдиқ", "ҳужжат рақами", "асос ҳужжат", "ҳужжат санаси", "манзил", "изоҳ",
    "иш куни", "ишкуни", "кўчирилган иш куни", "байрам", "дам олиш", "дам олиш куни",
}
# Hujjatlashtirish, konsol buyruqlari va tekshiruv xabarlari (hujjat matni — DOC_RU, quyida tekshiriladi)
SKIP_FILES = {"openapi.py", "schema.py", "acceptance.py", "conf.py", "admin.py",
              "services/protocol.py", "services/readiness.py",
              "services/integrity.py", "services/lang.py", "services/lang_ru.py"}


def _template(node) -> str:
    if isinstance(node, ast.Constant):
        return node.value
    out, i = [], 0
    for v in node.values:
        if isinstance(v, ast.Constant):
            out.append(v.value)
        else:
            out.append("{%d}" % i)
            i += 1
    return "".join(out)


def message_templates() -> dict:
    found = {}
    for path in sorted(APP.rglob("*.py")):
        rel = path.relative_to(APP).as_posix()
        if rel.split("/")[0] in ("tests", "migrations", "management") or rel in SKIP_FILES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
                first = n.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    skip.add(id(first.value))
            if isinstance(n, ast.JoinedStr):
                skip.update(id(v) for v in n.values)
        for n in ast.walk(tree):
            if id(n) in skip:
                continue
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and CYR.search(n.value):
                text = n.value
            elif isinstance(n, ast.JoinedStr) and any(isinstance(v, ast.Constant) and CYR.search(v.value) for v in n.values):
                text = _template(n)
            else:
                continue
            found.setdefault(text, f"{rel}:{n.lineno}")
    return found


class CatalogCoverageTest(SimpleTestCase):
    def test_every_message_has_russian(self):
        missing = []
        for text, where in message_templates().items():
            if len(text) <= 1 or text in NOT_MESSAGES:
                continue
            # "...: " + qo'shimcha va " (…)" qo'shimchasi katalogda {0} bilan
            if text in DOC_RU:
                continue
            key = text if text in RU else (text + "{0}" if text + "{0}" in RU else "{0}" + text)
            if key not in RU:
                missing.append(f"{where}: {text!r}")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_placeholders_match(self):
        ph = re.compile(r"\{\d+\}")
        bad = [k for k, v in RU.items() if sorted(ph.findall(k)) != sorted(ph.findall(v))]
        self.assertEqual(bad, [])


class ApiLanguageTest(OrderApiBase):
    def test_error_message_follows_accept_language(self):
        url = f"{BASE}/orders/00000000-0000-0000-0000-000000000000/"
        self.as_(self.m_user)
        ru = self.client.get(url, HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual(ru.status_code, 404)
        self.assertEqual(ru.data["message"], "Заявка не найдена или нет доступа")
        uz = self.client.get(url, HTTP_ACCEPT_LANGUAGE="uz")
        self.assertEqual(uz.data["message"], "Buyurtma topilmadi yoki ochish huquqi yo'q")
        self.assertEqual(uz.data["detail"]["detail"], "Buyurtma topilmadi yoki ochish huquqi yo'q")
        self.assertEqual(self.client.get(url).data["message"], "Buyurtma topilmadi yoki ochish huquqi yo'q")

    def test_notifications_follow_language_but_keep_user_text(self):
        d = self.create_draft()
        order_id = d["id"]
        YashilNotification.objects.create(recipient_user=self.m_user, membership=self.m_cab, kind="order_returned",
                                          title="Буюртма YM-1 тузатишга қайтарилди", body="Манзилни аниқлаштиринг", order_id=order_id)
        YashilNotification.objects.create(recipient_user=self.m_user, membership=self.m_cab, kind="order_accepted",
                                          title="Буюртма YM-1 ижрога қабул қилинди", body="Етказиш муддати: 01.04.2027", order_id=order_id)
        self.as_(self.m_user)
        rows = self.client.get(f"{BASE}/notifications/", HTTP_ACCEPT_LANGUAGE="ru").data["results"]
        by_kind = {r["kind"]: r for r in rows}
        self.assertEqual(by_kind["order_returned"]["title"], "Заявка YM-1 возвращена на исправление")
        self.assertEqual(by_kind["order_returned"]["body"], "Манзилни аниқлаштиринг")
        self.assertEqual(by_kind["order_accepted"]["body"], "Срок поставки: 01.04.2027")
        rows = self.client.get(f"{BASE}/notifications/", HTTP_ACCEPT_LANGUAGE="uz").data["results"]
        by_kind = {r["kind"]: r for r in rows}
        self.assertEqual(by_kind["order_returned"]["title"], "Buyurtma YM-1 tuzatishga qaytarildi")
        self.assertEqual(by_kind["order_returned"]["body"], "Манзилни аниқлаштиринг")
        self.assertEqual(by_kind["order_accepted"]["body"], "Yetkazish muddati: 01.04.2027")

    def test_success_payload_messages_translated(self):
        self.as_(self.x_user)  # boshqa mahallaga xo'jalik biriktirilmagan
        url = f"{BASE}/suppliers/for-mahalla/{self.other_mahalla.pk}/"
        self.assertEqual(self.client.get(url, HTTP_ACCEPT_LANGUAGE="ru").data["forest"]["message"], "Хозяйство не прикреплено")
        self.assertEqual(self.client.get(url, HTTP_ACCEPT_LANGUAGE="uz").data["forest"]["message"], "Xo'jalik biriktirilmagan")
