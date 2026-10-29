"""
Versiyali modul qoidalari (TZ §24.1; plans §11.1-9).

    get(key, on=None)                       -> qiymat (on sanasida kuchda bo'lgan versiya yoki standart)
    set_value(key, value, user, effective_from=None, note="", today=None) -> YashilSetting
    snapshot(on=None)                       -> admin ekrani uchun ro'yxat

Qoidalar o'zgarsa eski buyurtmalar yashirin qayta hisoblanmaydi: ko'rib chiqish
muddati birinchi yuborish sanasidagi qoida bilan, yetkazish muddati qabul sanasidagi
qoida bilan hisoblanadi. O'tgan sanadan kuchga kiritish taqiqlanadi.
"""
from datetime import date

from django.core.cache import cache
from django.utils import timezone

from apps.yashil.models import YashilSetting

CACHE_KEY = "yashil:rules:v1"
CACHE_TTL = 60

RULES = {
    "review_workdays": {"type": "int", "min": 1, "max": 30, "default": 3,
                        "label": "Кўриб чиқиш муддати (уюшма + етказиб берувчи жами), иш куни"},
    "delivery_workdays": {"type": "int", "min": 1, "max": 60, "default": 10,
                          "label": "Етказиш муддати (ижрога қабулдан), иш куни"},
    "act_review_reminder_days": {"type": "int", "min": 1, "max": 30, "default": 3,
                                 "label": "Далолатнома тасдиғи эслатмаси, иш кунидан кейин"},
    "forest_negative_stock_allowed": {"type": "bool", "default": True,
                                      "label": "Ўрмон хўжалигида манфий қолдиққа рухсат (ДМда ҳар доим қатъий)"},
}


class RuleError(ValueError):
    def __init__(self, message, field="value"):
        super().__init__(message)
        self.field = field


def _today() -> date:
    from apps.yashil.services.workdays import local_date

    return local_date(timezone.now())


def _rows() -> list[tuple]:
    rows = cache.get(CACHE_KEY)
    if rows is None:
        rows = list(YashilSetting.objects.order_by("key", "-effective_from", "-version").values_list("key", "effective_from", "version", "value"))
        cache.set(CACHE_KEY, rows, CACHE_TTL)
    return rows


def invalidate() -> None:
    cache.delete(CACHE_KEY)


def get(key: str, on: date | None = None):
    if key not in RULES:
        raise RuleError(f"Номаълум қоида: {key}", "key")
    on = on or _today()
    for k, eff, _v, value in _rows():
        if k == key and eff <= on:
            return value
    return RULES[key]["default"]


def _validate(key: str, value):
    spec = RULES.get(key)
    if spec is None:
        raise RuleError(f"Номаълум қоида: {key}", "key")
    if spec["type"] == "bool":
        if not isinstance(value, bool):
            raise RuleError("Қиймат true ёки false бўлиши керак")
        return value
    if isinstance(value, bool):
        raise RuleError("Қиймат бутун сон бўлиши керак")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise RuleError("Қиймат бутун сон бўлиши керак")
    if str(number) != str(value).strip():
        raise RuleError("Қиймат бутун сон бўлиши керак")
    if not spec["min"] <= number <= spec["max"]:
        raise RuleError(f"Қиймат {spec['min']}–{spec['max']} оралиғида бўлиши керак")
    return number


def set_value(key: str, value, user, effective_from: date | None = None, note: str = "", today: date | None = None) -> YashilSetting:
    value = _validate(key, value)
    today = today or _today()
    effective_from = effective_from or today
    if effective_from < today:
        raise RuleError("Қоида ўтган санадан кучга киритилмайди (TZ 24.1)", "effective_from")
    last = YashilSetting.objects.filter(key=key).order_by("-version").first()
    obj = YashilSetting(key=key, value=value, effective_from=effective_from, version=(last.version + 1) if last else 1,
                        changed_by=user, note=(note or "")[:500])
    obj._history_user = user
    obj.save()
    invalidate()
    return obj


def snapshot(on: date | None = None) -> list[dict]:
    on = on or _today()
    out = []
    history = {}
    for row in YashilSetting.objects.select_related("changed_by").order_by("key", "-version"):
        history.setdefault(row.key, []).append(row)
    for key, spec in RULES.items():
        rows = history.get(key, [])
        out.append({
            "key": key, "label": spec["label"], "type": spec["type"], "min": spec.get("min"), "max": spec.get("max"),
            "default": spec["default"], "value": get(key, on),
            "pending": [{"value": r.value, "effective_from": r.effective_from.isoformat(), "version": r.version}
                        for r in sorted(rows, key=lambda r: r.version) if r.effective_from > on],
            "history": [{
                "version": r.version, "value": r.value, "effective_from": r.effective_from.isoformat(), "note": r.note,
                "changed_by": (f"{r.changed_by.last_name} {r.changed_by.first_name}".strip() or r.changed_by.email) if r.changed_by_id else "",
                "created_at": r.created_at.isoformat(),
            } for r in rows],
        })
    return out


# ----------------------------------------------------------------------------- qo'llanish yordamchilari
def review_workdays_for(order) -> int:
    """Ko'rib chiqish muddati — birinchi yuborish sanasidagi qoida bilan."""
    from apps.yashil.services.workdays import local_date

    on = local_date(order.first_submitted_at) if order.first_submitted_at else None
    return get("review_workdays", on)
