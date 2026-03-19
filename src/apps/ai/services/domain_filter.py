import re

STAT_URMON_KEYWORDS = {
    "hisobot", "report", "statement",
    "reja", "amalda", "foiz",
    "viloyat", "respublika", "tuman",
    "ormоn", "o‘rmon", "forest",
    "ko‘chat", "nihol", "plant",
    "deadline", "svod",
    "aggregatsiya", "jami",
    "reportitem", "statementcolumn",
    "staturmon", "stat", "urmon", "erp", "sayt"
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text


def is_stat_urmon_related(question: str) -> bool:
    question = normalize_text(question)
    words = set(question.split())

    # 2 ta keyword topilsa → related deb hisoblaymiz
    match_count = len(words.intersection(STAT_URMON_KEYWORDS))
    return match_count >= 1