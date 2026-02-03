from decimal import Decimal

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



def ensure_plant_plans_exist(*, organization, statement):
    """
    Plant-based reportlar uchun VALIDATSIYA

    Qoidalar:
    1) Plan mavjud bo‘lishi shart
    2) Kamida 1 ta PlantPlan bo‘lishi shart
    3) Kamida 1 ta PlantPlanItem bo‘lishi shart
    4) Kamida 1 ta PlantPlanItem.plan_value > 0 bo‘lishi shart
    """

    # 1️⃣ PLAN BORLIGINI TEKSHIRAMIZ
    plans = Plan.objects.filter(
        organization=organization,
        statement=statement
    )

    if not plans.exists():
        raise serializers.ValidationError({
            "non_field_errors": [
                "Bu hisobot uchun reja (plan) yaratilmagan."
            ]
        })

    # 2️⃣ PLANTPLAN BORLIGINI TEKSHIRAMIZ
    plant_plans = PlantPlan.objects.filter(
        plan__in=plans
    )

    if not plant_plans.exists():
        raise serializers.ValidationError({
            "non_field_errors": [
                "Bu hisobot uchun o‘simliklar (plant) bo‘yicha reja yaratilmagan."
            ]
        })

    # 3️⃣ QAYSI USTUNLAR REJALIK EKANINI ANIQLAYMIZ
    plan_columns = StatementColumn.objects.filter(
        statement=statement,
        status_plan__isnull=False,
        is_user_input=True
    )

    if not plan_columns.exists():
        # Agar bu statementda umuman plan talab qilinmasa
        return

    # 4️⃣ PLANTPLANITEM LARNI TEKSHIRAMIZ
    plant_plan_items = PlantPlanItem.objects.filter(
        plant_plan__in=plant_plans,
        column__in=plan_columns
    )

    if not plant_plan_items.exists():
        raise serializers.ValidationError({
            "non_field_errors": [
                "Bu hisobot uchun plant bo‘yicha reja ustunlari to‘ldirilmagan."
            ]
        })

    # 5️⃣ KAMIDA BITTA > 0 QIYMAT BORLIGINI TEKSHIRAMIZ
    has_positive_value = plant_plan_items.filter(
        plan_value__gt=Decimal("0")
    ).exists()

    if not has_positive_value:
        raise serializers.ValidationError({
            "non_field_errors": [
                "Bu hisobot uchun plant bo‘yicha reja qiymatlari 0 dan katta emas."
            ]
        })
