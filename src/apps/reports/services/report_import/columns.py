# apps/reports/services/report_import/columns.py
"""
Berilgan Statement uchun foydalanuvchi import qilishi mumkin bo'lgan
"Amalda" ustunlarni qaytaradi.

Amalda ustun = StatementColumn WHERE:
    - status_plan IS NULL       (Reja ustuni EMAS)
    - is_user_input = True      (avto-hisoblangan EMAS)
    - is_organization = False   (tashkilot ustuni EMAS)
    - parent IS NOT NULL        (ilova/ildiz sarlavhasi EMAS)
    - children IS NULL          (guruh sarlavhasi EMAS — faqat leaf)

Template generator VA parser bir xil ustun ro'yxatidan foydalanadi —
shu funksiya orqali.

Bu yerda ustun sarlavhalari bilan ishlash yordamchilari ham turadi
(`StatementColumnIndex`): bitta statement ichida bir xil nomli ustunlar
ko'p bo'ladi ("Amalda" har oy uchun alohida), shuning uchun ustunni
faqat nomi bilan emas, ota-ona zanjiri (path) bilan aniqlash kerak.
"""

import re

from apps.reports.models import Plant, StatementColumn

# Template sarlavhasida path segmentlarini ajratuvchi belgi:
#   "Yanvar » Amalda"
PATH_SEPARATOR = " » "

# Sarlavha matnini path segmentlariga ajratish (faqat nom to'liq mos
# kelmagan holatda ishlatiladi — "Telefon raqami / Telegram" kabi
# nomlarni buzib yubormaslik uchun).
_PATH_SPLIT_RE = re.compile(r"\s*[»→|]\s*|\s+/\s+")

# ‘ ’ ʻ ʼ ` ´ ′ ʹ → ' : bazadagi va Excel'dagi apostroflar har xil bo'ladi
_APOSTROPHES = {ord(ch): "'" for ch in "‘’ʻʼ`´′ʹ"}
_WHITESPACE_RE = re.compile(r"\s+")

# Sarlavha oxiridagi tartib raqami: "Yetishtirilgan mahsulot (tn) (2)"
_ORDINAL_RE = re.compile(r"\s*\((\d+)\)$")

TITLE_FIELDS = ("title_uz", "title_ru", "title")


def normalize_title(value):
    """
    Sarlavhani solishtirish uchun bir ko'rinishga keltiradi:
    kichik harf, apostroflar bir xil, ortiqcha bo'shliqlar olib tashlangan.
    """
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ").translate(_APOSTROPHES)
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def split_title_path(value):
    """
    "Yanvar » Amalda" → ["yanvar", "amalda"].
    Ajratuvchi bo'lmasa — bitta elementli ro'yxat.
    """
    normalized = normalize_title(value)
    if not normalized:
        return []
    return [part for part in _PATH_SPLIT_RE.split(normalized) if part]


def strip_ordinal(text):
    """
    "yetishtirilgan mahsulot (tn) (2)" → ("yetishtirilgan mahsulot (tn)", 2)

    Ba'zi jadvallarda bir xil nomli, bir xil ota-onali ikkita ustun bor —
    ularni faqat tartib raqami ajratadi.
    """
    match = _ORDINAL_RE.search(text or "")
    if not match:
        return text, None
    return _WHITESPACE_RE.sub(" ", text[:match.start()]).strip(), int(match.group(1))


def ordering_key(ordering):
    """
    "1.1.10" → (1, 1, 10). Matn sifatida saralashda "1.1.10" < "1.1.2"
    bo'lib qolmasligi uchun.
    """
    parts = []
    for chunk in str(ordering or "").split("."):
        parts.append(int(chunk) if chunk.isdigit() else 0)
    return tuple(parts)


def get_importable_columns(statement):
    """
    Statement uchun import qilinadigan barcha leaf ustunlarni
    QuerySet sifatida qaytaradi.

    Tartib uchun `ordering_key` bilan saralang — `ordering` matn maydoni
    bo'lgani uchun DB tartibi "1.1.10" ni "1.1.2" dan oldin qo'yadi.
    """
    return (
        StatementColumn.objects
        .filter(
            statement=statement,
            is_organization=False,
            is_user_input=True,
            status_plan__isnull=True,
            parent__isnull=False,
            children__isnull=True,
        )
        .select_related("parent")
        .order_by("ordering")
    )


def is_plant_based_statement(statement):
    """
    Jadval o'simliklar kesimidami?

    `use_plant_plan` ga ishonib bo'lmaydi — u **Reja** moduliniki
    ("reja o'simlik bo'yicha kiritiladi") va bazada faqat bitta jadvalda
    True. Amalda esa hisobot qatorlari o'simlikka bog'lanadigan jadvallar
    ko'proq (masalan "Shakl 8-O'X", "Ko'chatxona va Niholxona Jami").

    Shuning uchun uchta dalilning istalgan biri yetarli:
      1. use_plant_plan = True
      2. shu jadval bo'yicha plantlik hisobot mavjud
      3. jadvalga leaf o'simliklar biriktirilgan (yangi jadval — hali
         hisobot yo'q bo'lsa ham shablon to'g'ri chiqishi uchun)
    """
    if getattr(statement, "use_plant_plan", False):
        return True

    from apps.reports.models import Report

    if Report.objects.filter(statement=statement, is_plant_based=True).exists():
        return True

    return Plant.objects.filter(statement=statement, children__isnull=True).exists()


class StatementColumnIndex:
    """
    Statement ustunlari daraxtini bir marta yuklab, sarlavha bilan
    ishlash uchun kerakli barcha ma'lumotni beradi.

    Nima uchun kerak: bitta statement ichida "Amalda" nomli 12 ta ustun
    bo'lishi mumkin (har oy uchun). Ularni faqat nom bo'yicha farqlab
    bo'lmaydi — ota-ona zanjiri (masalan "1-chorak → Yanvar → Amalda")
    kerak bo'ladi.
    """

    def __init__(self, statement, lang="uz"):
        self.statement = statement
        self.lang = lang

        self.all_columns = list(
            StatementColumn.objects.filter(statement=statement)
        )
        self._by_id = {str(c.id): c for c in self.all_columns}
        self._title_variants_cache = {}

        self.importable = sorted(
            get_importable_columns(statement),
            key=lambda c: ordering_key(c.ordering),
        )
        self.importable_ids = {str(c.id) for c in self.importable}

        # leaf nomi → shu nomdagi importable ustunlar
        self._by_leaf_title = {}
        for column in self.importable:
            for title in self.title_variants(column):
                self._by_leaf_title.setdefault(title, []).append(column)

        # statementdagi BARCHA ustun nomlari — sarlavha satrini
        # ma'lumot satridan ajratish uchun
        self.known_titles = set()
        for column in self.all_columns:
            self.known_titles.update(self.title_variants(column))

        # to'liq yo'l → ustun(lar). Excel sarlavhasi "Daromad ilovasi →
        # 2026 yil ... → 1-chorak → Yanvar → Amalda" ko'rinishida
        # bo'lgani uchun ustunni aynan shu yo'l bo'yicha topamiz.
        self._by_path = {}
        for column in self.all_columns:
            for path in self._path_variants(column):
                self._by_path.setdefault(path, []).append(column)

        self._importable_paths = {
            str(column.id): self._path_variants(column)
            for column in self.importable
        }

        # yo'llar bir marta hisoblanadi — label() uchun
        self._display_paths = {
            str(column.id): self.display_path(column)
            for column in self.importable
        }
        self._normalized_paths = {
            column_id: [normalize_title(title) for title in path]
            for column_id, path in self._display_paths.items()
        }

    # ── Nomlar ──

    def title_variants(self, column):
        """Ustunning barcha til variantlaridagi normallashtirilgan nomi."""
        column_id = str(column.id)
        cached = self._title_variants_cache.get(column_id)
        if cached is not None:
            return cached

        variants = set()
        for field in TITLE_FIELDS:
            title = normalize_title(getattr(column, field, None))
            if title:
                variants.add(title)

        self._title_variants_cache[column_id] = variants
        return variants

    def display_title(self, column):
        """Foydalanuvchiga ko'rsatiladigan nom (tanlangan tilda)."""
        return (
            getattr(column, f"title_{self.lang}", None)
            or column.title_uz
            or column.title
        )

    # ── Daraxt ──

    def ancestors(self, column):
        """Ustunning ota-onalari (ildizdan boshlab) ro'yxati."""
        chain = []
        seen = {str(column.id)}  # noto'g'ri ma'lumotda halqa bo'lsa — to'xtaymiz
        current = self._by_id.get(str(column.parent_id)) if column.parent_id else None
        while current is not None and str(current.id) not in seen:
            seen.add(str(current.id))
            chain.append(current)
            current = (
                self._by_id.get(str(current.parent_id))
                if current.parent_id else None
            )
        chain.reverse()
        return chain

    def ancestor_title_variants(self, column):
        """Ota-onalar nomlari (ildizdan boshlab), har biri variantlar to'plami."""
        return [self.title_variants(parent) for parent in self.ancestors(column)]

    def display_path(self, column):
        """["1-chorak", "Yanvar", "Amalda"] — ko'rsatish uchun to'liq yo'l."""
        return [
            self.display_title(node)
            for node in (*self.ancestors(column), column)
        ]

    def _path_variants(self, column):
        """
        Ustunning to'liq yo'li — har bir til uchun alohida:
            ("daromad ilovasi", "2026 yil ...", "1-chorak", "yanvar", "amalda")
        """
        chain = (*self.ancestors(column), column)
        variants = set()
        for field in TITLE_FIELDS:
            path = tuple(
                normalize_title(getattr(node, field, None)) for node in chain
            )
            if all(path):
                variants.add(path)
        return variants

    def candidates_by_leaf_title(self, title):
        """Berilgan nomdagi importable ustunlar."""
        return self._by_leaf_title.get(normalize_title(title), [])

    def columns_by_path(self, path):
        """To'liq yo'l bo'yicha ustun(lar) — statementdagi BARCHA ustunlar ichidan."""
        return self._by_path.get(tuple(path), [])

    def importable_by_path_suffix(self, path):
        """
        Yo'lning oxirgi qismi bo'yicha importable ustunlar.

        Shablonda sarlavha qisqartirilgan bo'ladi ("Yanvar » Amalda"),
        shuning uchun to'liq yo'lning oxiriga to'g'ri kelishi yetarli.
        """
        path = tuple(path)
        if not path:
            return []
        matches = []
        for column in self.importable:
            for variant in self._importable_paths[str(column.id)]:
                if len(variant) >= len(path) and variant[-len(path):] == path:
                    matches.append(column)
                    break
        return matches

    def importable_by_path_ordinal(self, path, ordinal):
        """
        Bir xil yo'lli ustunlar ichidan tartib raqami bo'yicha tanlaydi
        (shablondagi "... (2)" sarlavhasi uchun).
        """
        matches = self.importable_by_path_suffix(path)
        if 1 <= ordinal <= len(matches):
            return matches[ordinal - 1]
        return None

    def label(self, column):
        """
        Excel sarlavhasi uchun nom: statement ichida yagona bo'lishi
        kafolatlangan eng qisqa yo'l.

            "Tumanlar nomi"            — nomi o'zi yagona bo'lsa
            "Yanvar » Amalda"          — "Amalda" takrorlansa
        """
        column_id = str(column.id)
        display_path = self._display_paths.get(column_id) or self.display_path(column)
        own_path = self._normalized_paths.get(column_id) or [
            normalize_title(title) for title in display_path
        ]

        for depth in range(1, len(own_path) + 1):
            suffix = own_path[-depth:]
            clash = any(
                other_id != column_id and other_path[-depth:] == suffix
                for other_id, other_path in self._normalized_paths.items()
            )
            if not clash:
                return PATH_SEPARATOR.join(display_path[-depth:])

        # Bir xil to'liq yo'lli ikkita ustun bo'lsa (faqat `ordering` bilan
        # farq qiladi) — tartib raqami qo'shamiz: "... (1)", "... (2)"
        twins = [
            other_id
            for other_id, other_path in self._normalized_paths.items()
            if other_path == own_path
        ]
        position = twins.index(column_id) + 1 if column_id in twins else 1
        return f"{PATH_SEPARATOR.join(display_path)} ({position})"
