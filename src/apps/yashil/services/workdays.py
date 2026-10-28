"""
Ish kunlari hisobi (TZ §8).

Qoidalar:
- Vaqt zonasi Asia/Tashkent; hodisa kuni hisobga kirmaydi, keyingi ish kuni 1-kun.
- Shanba/yakshanba ish kuni emas; `holidays` — qo'shimcha dam olish (bayram),
  `workdays` — ko'chirilgan ish kunlari (dam olish kunida ishlanadi).
- Ko'rib chiqish 3 kuni segmentlardan yig'iladi: mahallaga qaytarilgan davr
  hisobdan chiqadi; qaytarish kuni (ish kuni bo'lsa) hisobga kiradi; qayta
  yuborilgach keyingi ish kunidan davom etadi, hisob nollanmaydi.

Funksiyalar sof (DB'siz); kalendar `Calendar` obyekti bilan beriladi.
`calendar_from_db()` CalendarDay jadvalidan o'qiydi va 1 soat keshlaydi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.cache import cache

TASHKENT = ZoneInfo("Asia/Tashkent")
REVIEW_WORKDAYS = 3
DELIVERY_WORKDAYS = 10
CALENDAR_CACHE_KEY = "yashil:calendar:v1"
CALENDAR_CACHE_TTL = 3600
_MAX_SCAN_DAYS = 3660  # cheksiz sikldan himoya (10 yil)


@dataclass(frozen=True)
class Calendar:
    holidays: frozenset = field(default_factory=frozenset)
    workdays: frozenset = field(default_factory=frozenset)

    def __post_init__(self):
        object.__setattr__(self, "holidays", frozenset(self.holidays))
        object.__setattr__(self, "workdays", frozenset(self.workdays))


def local_date(value: datetime | date) -> date:
    """UTC/aware datetime -> Asia/Tashkent sanasi. `date` bo'lsa o'zi qaytadi."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("UTC"))
        return value.astimezone(TASHKENT).date()
    return value


def is_workday(day: date, cal: Calendar) -> bool:
    if day in cal.workdays:
        return True
    if day in cal.holidays:
        return False
    return day.weekday() < 5


def add_workdays(start: date, n: int, cal: Calendar) -> date:
    """`start`dan keyingi n-ish kuni sanasi (start hisobga kirmaydi)."""
    if n <= 0:
        return start
    day, left, scanned = start, n, 0
    while left > 0:
        day += timedelta(days=1)
        scanned += 1
        if scanned > _MAX_SCAN_DAYS:
            raise ValueError("Ish kunlari hisobi juda uzun davrga cho'zildi")
        if is_workday(day, cal):
            left -= 1
    return day


def count_workdays(start: date, end: date, cal: Calendar) -> int:
    """(start, end] oralig'idagi ish kunlari soni; end <= start bo'lsa 0."""
    if end <= start:
        return 0
    total, day = 0, start
    while day < end:
        day += timedelta(days=1)
        if is_workday(day, cal):
            total += 1
    return total


def review_days_used(segments, today: date, cal: Calendar, total: int = REVIEW_WORKDAYS) -> int:
    """Segmentlar bo'yicha sarflangan ko'rib chiqish ish kunlari (yopiq + ochiq, `today`gacha)."""
    used = 0
    for start, end in segments:
        used += count_workdays(start, end if end is not None else today, cal)
    return used


def review_deadline(segments, cal: Calendar, total: int = REVIEW_WORKDAYS) -> date | None:
    """
    Ochiq segment uchun oxirgi muddat sanasi. Ochiq segment bo'lmasa None.
    Qolgan kunlar = total - yopiq segmentlarda sarflangan; 0 yoki manfiy bo'lsa
    muddat ochiq segment boshlangan kunning o'zi (allaqachon buzilgan).
    """
    segments = list(segments)
    if not segments or segments[-1][1] is not None:
        return None
    used_before = sum(count_workdays(s, e, cal) for s, e in segments[:-1])
    remaining = max(0, total - used_before)
    return add_workdays(segments[-1][0], remaining, cal)


def delivery_deadline(accepted_on: date, cal: Calendar, n: int = DELIVERY_WORKDAYS) -> date:
    return add_workdays(accepted_on, n, cal)


def overdue_workdays(deadline: date, today: date, cal: Calendar) -> int:
    """Muddatdan keyin o'tgan ish kunlari (deadline kuni 23:59:59 gacha buzilmagan)."""
    return count_workdays(deadline, today, cal)


def calendar_from_db(force: bool = False) -> Calendar:
    """CalendarDay jadvalidan Calendar; 1 soat keshlanadi (admin saqlaganda tozalanadi)."""
    if not force:
        cached = cache.get(CALENDAR_CACHE_KEY)
        if cached is not None:
            return cached
    from apps.yashil.models import CalendarDay

    holidays, workdays = set(), set()
    for day, kind in CalendarDay.objects.values_list("date", "kind"):
        (workdays if kind == CalendarDay.Kind.WORKDAY else holidays).add(day)
    cal = Calendar(holidays=frozenset(holidays), workdays=frozenset(workdays))
    cache.set(CALENDAR_CACHE_KEY, cal, CALENDAR_CACHE_TTL)
    return cal


def invalidate_calendar_cache() -> None:
    cache.delete(CALENDAR_CACHE_KEY)
