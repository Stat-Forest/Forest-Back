import re
from typing import Dict, List


class TerminologyNormalizer:
    APOSTROPHE_VARIANTS = ["'", "’", "‘", "ʼ", "ʻ", "`", "´"]
    DASH_VARIANTS = ["–", "—"]

    TERMINOLOGY_MAP: Dict[str, str] = {
        # english/russian -> uzbek business terms
        "deadline": "muddat",
        "report": "hisobot",
        "отчет": "hisobot",
        "plan": "reja",
        "план": "reja",
        "fact": "amalda",
        "факт": "amalda",
        "organization": "tashkilot",
        "организация": "tashkilot",
        "region": "viloyat",
        "область": "viloyat",
        "republic": "respublika",
        "республика": "respublika",
        "department": "bo'lim",
        "отдел": "bo'lim",
        "statement": "hisobot bo'limi",
        "statementcolumn": "ustun",
        "reportitem": "hisobot qatori",
        "reportiteminner": "ichki qiymat",
    }

    SPELLING_CORRECTIONS: Dict[str, str] = {
        "o'lim": "bo'lim",
        "olim": "bo'lim",
        "bolim": "bo'lim",
        "hisobotni": "hisobot",
        "hisobotlar": "hisobot",
        "rejani": "reja",
        "rejalar": "reja",
        "muddati": "muddat",
        "muddatlar": "muddat",
        "amaldagi": "amalda",
        "viloyati": "viloyat",
        "respublikasi": "respublika",
        "jamgarma": "jamg'arma",
        "kochat": "ko'chat",
        "urug ": "urug' ",
        "nihollar": "nihol",
        "ko'chatlar": "ko'chat",
    }

    DOMAIN_KEYWORDS: List[str] = [
        "stat urmon",
        "stat-urmon",
        "tizim",
        "hisobot",
        "hisobot bo'limi",
        "reja",
        "amalda",
        "muddat",
        "ustun",
        "tashkilot",
        "viloyat",
        "respublika",
        "bo'lim",
        "status",
        "accepted",
        "cancelled",
        "sent",
        "saved",
        "e-imzo",
        "imzo",
        "urug'",
        "urug' xarakati",
        "jamg'arma",
        "daromad",
        "ko'chat",
        "nihol",
        "o'simlik",
        "plant",
        "ichki qiymat",
        "hisobot qatori",
        "individual umumiy",
        "viloyat jami",
        "respublika jami",
        "deadline",
        "plan",
        "statement",
        "report",
    ]

    QUERY_EXPANSIONS: Dict[str, List[str]] = {
        "tashkilot": ["organization"],
        "hisobot": ["report", "statement", "hisobot bo'limi"],
        "muddat": ["deadline"],
        "reja": ["plan"],
        "amalda": ["fact"],
        "bo'lim": ["department"],
        "ustun": ["statementcolumn"],
        "urug'": ["urug' xarakati"],
        "ko'chat": ["plant", "nihol"],
        "nihol": ["plant", "ko'chat"],
        "jamg'arma": ["daromad"],
    }

    @classmethod
    def normalize_text(cls, text: str) -> str:
        if not text:
            return ""

        normalized = text.strip().lower()

        for ch in cls.APOSTROPHE_VARIANTS:
            normalized = normalized.replace(ch, "'")

        for ch in cls.DASH_VARIANTS:
            normalized = normalized.replace(ch, "-")

        normalized = normalized.replace("o‘", "o'").replace("g‘", "g'")
        normalized = normalized.replace("oʻ", "o'").replace("gʻ", "g'")
        normalized = normalized.replace("oʼ", "o'").replace("gʼ", "g'")
        normalized = normalized.replace("ў", "o'").replace("ғ", "g'")

        normalized = re.sub(r"[,:;!?()\[\]{}\"]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        normalized = cls._replace_whole_words(normalized, cls.SPELLING_CORRECTIONS)
        normalized = cls._replace_whole_words(normalized, cls.TERMINOLOGY_MAP)

        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @classmethod
    def _replace_whole_words(cls, text: str, replacements: Dict[str, str]) -> str:
        for source, target in replacements.items():
            pattern = rf"(?<!\w){re.escape(source)}(?!\w)"
            text = re.sub(pattern, target, text, flags=re.IGNORECASE)
        return text

    @classmethod
    def extract_key_terms(cls, text: str) -> List[str]:
        normalized = cls.normalize_text(text)
        found = [term for term in cls.DOMAIN_KEYWORDS if term in normalized]
        return sorted(set(found))

    @classmethod
    def is_domain_specific(cls, text: str) -> bool:
        normalized = cls.normalize_text(text)
        return any(term in normalized for term in cls.DOMAIN_KEYWORDS)

    @classmethod
    def expand_query_terms(cls, text: str) -> List[str]:
        normalized = cls.normalize_text(text)
        terms = cls.extract_key_terms(normalized)
        expanded = set(terms)

        for term in terms:
            for alias in cls.QUERY_EXPANSIONS.get(term, []):
                expanded.add(alias)

        # original important words ham qolsin
        for token in normalized.split():
            if len(token) >= 3:
                expanded.add(token)

        return sorted(expanded)