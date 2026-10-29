"""
Kechikish ustunlari (Order.review_due / late_workdays / overdue_stage).

Ish kunlari kalendari SQL'da hisoblanmaydi, shuning uchun reestrdagi
`overdue=1` filtri va «Муддати бузилган» kartasi uchun natija ustunlarda
saqlanadi: har holat o'tishida (`transitions._event`) va har ertalab
(`yashil.deadline_reminders`) qayta hisoblanadi. Buyurtma kartasidagi
`deadline_info` esa har so'rovda bugungi kun bilan hisoblanadi.
"""
from datetime import date

from django.utils import timezone

from apps.yashil.models import DELIVERY_STATES, REVIEW_STATES, Order
from apps.yashil.services.workdays import calendar_from_db, local_date, overdue_workdays, review_deadline

FIELDS = ("review_due", "late_workdays", "overdue_stage")


def compute(order: Order, today: date, cal) -> dict:
    """Sof hisob: buyurtma holati va segmentlaridan uchta qiymat."""
    review_due, late, stage = None, 0, ""
    if order.state in REVIEW_STATES:
        from apps.yashil.services.rules import review_workdays_for

        review_due = review_deadline(order.review_segments_as_tuples_dates(), cal, review_workdays_for(order))
        if review_due:
            late = overdue_workdays(review_due, today, cal)
            stage = "review" if late else ""
    elif order.state in DELIVERY_STATES and order.delivery_due:
        late = overdue_workdays(order.delivery_due, today, cal)
        stage = "delivery" if late else ""
    return {"review_due": review_due, "late_workdays": late, "overdue_stage": stage}


def recalc_order(order: Order, today: date | None = None, cal=None) -> dict:
    """Bitta buyurtma; o'zgargan bo'lsa DB'da yangilaydi (instance ham yangilanadi)."""
    today = today or local_date(timezone.now())
    cal = cal or calendar_from_db()
    values = compute(order, today, cal)
    if any(getattr(order, f) != values[f] for f in FIELDS):
        Order.objects.filter(pk=order.pk).update(**values)
        for f in FIELDS:
            setattr(order, f, values[f])
    return values


def recalc_all(today: date | None = None, cal=None) -> int:
    """Ochiq buyurtmalar (ko'rib chiqish + yetkazish) bo'yicha; yangilangan qatorlar soni."""
    today = today or local_date(timezone.now())
    cal = cal or calendar_from_db()
    changed = 0
    qs = Order.objects.filter(state__in=REVIEW_STATES | DELIVERY_STATES).prefetch_related("review_segments")
    for order in qs.iterator(chunk_size=500):
        values = compute(order, today, cal)
        if any(getattr(order, f) != values[f] for f in FIELDS):
            Order.objects.filter(pk=order.pk).update(**values)
            changed += 1
    # Yakuniy holatga o'tganlarda qoldiq kechikish bo'lmasin (eski yozuvlar)
    changed += Order.objects.exclude(state__in=REVIEW_STATES | DELIVERY_STATES).exclude(
        late_workdays=0, overdue_stage="", review_due__isnull=True,
    ).update(late_workdays=0, overdue_stage="", review_due=None)
    if changed:
        from apps.yashil.services.stats import bump_version

        bump_version()
    return changed
