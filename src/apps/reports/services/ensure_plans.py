from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.reports.models import StatementColumn, Plan, PlanItem


def _is_empty_plan_value(raw_value) -> bool:
    """Plan qiymati bo‘sh yoki nolga tengligini tekshiradi."""
    if raw_value in (None, "", 0, "0"):
        return True
    try:
        value = Decimal(str(raw_value))
        return value == 0
    except (InvalidOperation, TypeError, ValueError):
        return True


def resolve_actual_plan_year(deadline_year: int, status_plan: str) -> int:
    """
    status_plan bo‘yicha plan yili qanday olinishi:
    - yillik → har doim o'tgan yil (deadline_year - 1)
    - choraklik / oylik → aynan deadline_year
    - yanvar–dekabr → deadline_year
    """
    if not status_plan:
        return deadline_year  # plan yo‘q bo‘lsa shu yil ishlatiladi

    status_plan = status_plan.lower()

    # YILLIK — har doim o'tgan yil
    if status_plan in ["yillik", "yillik_total"]:
        return deadline_year

    # CHORAKLIK → ayni yil
    if status_plan.startswith("chorak_"):
        return deadline_year

    # OYLIK (yanvar...dekabr)
    if status_plan in [
        "yanvar", "fevral", "mart", "aprel", "may", "iyun",
        "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"
    ]:
        return deadline_year

    return deadline_year



def ensure_plans_exist(*, organization, statement, year):
    print(f"🔍 [START] ensure_plans_exist: org={organization}, statement={statement}, deadline_year={year}")

    # 1️⃣ Rejalik ustunlarni topamiz
    plan_columns = list(
        StatementColumn.objects.filter(
            statement=statement,
            status_plan__isnull=False,
            is_user_input=True,
        )
    )

    print(f"📌 Found {len(plan_columns)} plan_columns:")
    for col in plan_columns:
        print(f"   🧩 Column: {col.id} | ordering={col.ordering} | status_plan={col.status_plan}")

    if not plan_columns:
        print("⚠️ No plan columns → skipping check")
        return

    # 2️⃣ status_plan → actual_plan_year'ni topamiz
    unique_statuses = {col.status_plan for col in plan_columns if col.status_plan}
    if len(unique_statuses) > 1:
        print("⚠️ WARN: Multiple status_plan detected, using the first one")

    status_plan = next(iter(unique_statuses))
    actual_plan_year = resolve_actual_plan_year(year, status_plan)

    print(f"🧠 status_plan={status_plan} → actual_plan_year={actual_plan_year}")

    # 3️⃣ Plan obyektini izlaymiz
    try:
        plan = Plan.objects.get(
            organization=organization,
            statement=statement,
            year=actual_plan_year,
        )
        print(f"✅ Found Plan: {plan}")
    except Plan.DoesNotExist:
        print("❌ Plan not found → all columns missing")
        raise _raise_validation(plan_columns)

    # 4️⃣ PlanItemlarni yuklaymiz
    plan_items = list(
        PlanItem.objects.filter(
            plan=plan,
            column__in=plan_columns,
        ).select_related("column")
    )

    print(f"📦 Found {len(plan_items)} PlanItem(s)")
    items_by_column_id = {str(pi.column_id): pi for pi in plan_items}

    # 5️⃣ Har bir ustun tekshiriladi
    missing = []
    for col in plan_columns:
        pi = items_by_column_id.get(str(col.id))
        if pi is None or _is_empty_plan_value(pi.plan_value):
            print(f"❌ Missing or zero: {col.ordering} – {col.title}")
            missing.append(col)
        else:
            print(f"✅ OK: {col.ordering} → {pi.plan_value}")

    if missing:
        _raise_validation(missing)

    print("✅ [DONE] All required plans exist and valid.")



def _raise_validation(missing_columns):
    """Xatolik chiqarish yordamchi funksiyasi."""
    cols_str = ", ".join(f"{c.ordering} – {getattr(c, 'title_uz', c.title)}" for c in missing_columns)
    msg = _(
        "Bu hisobot uchun reja kiritilmagan. "
        "Quyidagi ustunlar bo‘yicha reja (plan) mavjud emas yoki 0 ga teng: %(cols)s. "
        "Iltimos, bo‘lim administratori avval reja kiritgandan so‘ng hisobot yarating."
    ) % {"cols": cols_str}
    print("❌ [FAIL] Missing plan columns:", cols_str)
    raise serializers.ValidationError({"non_field_errors": [msg]})


def get_year_from_submit_at(submit_at: str) -> int:
    """Deadline.submit_at formatidan yilni ajratadi (masalan: '2025-CHORAK_1' → 2025)."""
    if not submit_at or not isinstance(submit_at, str):
        raise ValueError("submit_at bo‘sh yoki noto‘g‘ri formatda")
    try:
        return int(submit_at.split("-")[0])
    except Exception:
        raise ValueError(f"submit_at qiymatidan yilni ajratib bo‘lmadi: {submit_at}")
