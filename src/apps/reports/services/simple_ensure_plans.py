from decimal import Decimal

from django.db.models import Q
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.reports.models import Plan, PlanItem, StatementColumn, PlantPlanItem, PlantPlan


def ensure_plans_exist_simple(*, organization, statement):
    """
    Plan mavjudligini tekshiradi.
    statement ichidagi barcha rejalik columnlar uchun hech bo‘lmaganda 1ta PlanItem mavjud bo‘lishi kerak.
    """
    print(f"🔍 [START] ensure_plans_exist_simple: org={organization}, statement={statement}")

    # 1️⃣ Rejalik ustunlar
    plan_columns = list(
        StatementColumn.objects.filter(
            statement=statement,
            status_plan__isnull=False,
            is_user_input=True,
        )
    )
    print(f"📌 Found {len(plan_columns)} plan_columns")

    if not plan_columns:
        print("⚠️ No plan columns → skipping check")
        return

    # 2️⃣ Plan mavjudligini tekshir
    plans = Plan.objects.filter(
        organization=organization,
        statement=statement
    ).only("id")

    if not plans.exists():
        print("❌ Plan not found for this statement and organization.")
        raise _raise_missing_plan_error(plan_columns)

    # 3️⃣ PlanItem larni yuklash
    plan_items = PlanItem.objects.filter(
        plan__in=plans,
        column__in=plan_columns
    ).select_related("column")

    if not plan_items.exists():
        print("❌ No PlanItems at all.")
        raise _raise_missing_plan_error(plan_columns)

    # 4️⃣ Foydali PlanItem bormi?
    # usable_items = [item for item in plan_items if not _is_empty_plan_value(item.plan_value)]
    plan_items = PlanItem.objects.filter(
        plan__in=plans,
        column__in=plan_columns
    ).select_related("column")
    if not plan_items.exists():
        print("❌ No PlanItems at all.")
        raise _raise_missing_plan_error(plan_columns)

    print("✅ [DONE] At least one usable plan item exists.")


def _raise_missing_plan_error(missing_columns):
    """Xatolik chiqarish"""
    cols_str = ", ".join(f"{c.ordering} – {getattr(c, 'title_uz', c.title)}" for c in missing_columns)
    msg = _(
        "Bu hisobot uchun reja kiritilmagan. "
        "Quyidagi ustunlar bo‘yicha reja (plan) mavjud emas yoki 0 ga teng."
        "Iltimos, bo‘lim administratori avval reja kiritgandan so‘ng hisobot yarating."
    ) % {"cols": cols_str}
    raise serializers.ValidationError({"non_field_errors": [msg]})


from decimal import Decimal
from rest_framework import serializers
from apps.reports.models import (
    Plan,
    PlantPlan,
    PlantPlanItem,
    StatementColumn,
)


def ensure_plant_plans_exist(*, organization, statement):
    """
    Universal reja validatsiyasi:

    ✔ Oddiy reja mavjudmi
    ✔ Plantlik reja kerakmi yoki yo‘qmi aniqlaydi
    ✔ Kerak bo‘lsa plant bo‘yicha tekshiradi
    """

    # ===============================
    # 1️⃣ BU STATEMENT REJA TALAB QILADIMI?
    # ===============================
    plan_columns = StatementColumn.objects.filter(
        statement=statement,
        status_plan__isnull=False,
        is_user_input=True,
    )

    # Agar umuman rejalik column bo‘lmasa → hech narsa tekshirilmaydi
    if not plan_columns.exists():
        return

    # ===============================
    # 2️⃣ ODDIY PLAN BORLIGI
    # ===============================
    plans = Plan.objects.filter(
        organization=organization,
        statement=statement,
    )

    if not plans.exists():
        raise serializers.ValidationError({
            "non_field_errors": ["Bu hisobot uchun reja (plan) yaratilmagan."]
        })

    # ===============================
    # 3️⃣ BU STATEMENT PLANTLIKMI?
    # ===============================
    has_plant_plans = PlantPlan.objects.filter(
        plan__in=plans
    ).exists()

    # ===============================
    # 🌱 AGAR PLANTLIK REJA BOR BO‘LSA
    # ===============================
    if has_plant_plans:

        plant_plan_items = PlantPlanItem.objects.filter(
            plant_plan__plan__in=plans,
            column__in=plan_columns
        )

        if not plant_plan_items.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    "Bu hisobot uchun plant bo‘yicha reja qiymatlari kiritilmagan."
                ]
            })

        if not plant_plan_items.filter(plan_value__gt=Decimal("0")).exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    "Plant bo‘yicha reja qiymatlari 0 dan katta emas."
                ]
            })

        return   # ✅ plantlik bo‘lsa shu yerda tugaydi

    # ===============================
    # 📄 AKS HOLDA — ODDIY PLANITEM
    # ===============================

    plan_items = PlanItem.objects.filter(
        plan__in=plans,
        column__in=plan_columns
    )

    if not plan_items.exists():
        raise serializers.ValidationError({
            "non_field_errors": [
                "Bu hisobot uchun reja ustunlari to‘ldirilmagan."
            ]
        })

    if not plan_items.filter(plan_value__gt=Decimal("0")).exists():
        raise serializers.ValidationError({
            "non_field_errors": [
                "Reja qiymatlari 0 dan katta emas."
            ]
        })

