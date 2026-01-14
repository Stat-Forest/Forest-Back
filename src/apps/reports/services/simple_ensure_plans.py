# from rest_framework import serializers
# from django.utils.translation import gettext_lazy as _
# from apps.reports.models import Plan, PlanItem, StatementColumn
# from apps.reports.services.ensure_plans import _is_empty_plan_value
#
#
# def ensure_plans_exist_simple(*, organization, statement):
#     """
#     Plan mavjudligini tekshiradi.
#     statement ichidagi barcha rejalik columnlar uchun hech bo‘lmaganda 1ta PlanItem mavjud bo‘lishi kerak.
#     """
#     print(f"🔍 [START] ensure_plans_exist_simple: org={organization}, statement={statement}")
#
#     # 1️⃣ Rejalik ustunlar
#     plan_columns = list(
#         StatementColumn.objects.filter(
#             statement=statement,
#             status_plan__isnull=False,
#             is_user_input=True,
#         )
#     )
#     print(f"📌 Found {len(plan_columns)} plan_columns")
#
#     if not plan_columns:
#         print("⚠️ No plan columns → skipping check")
#         return
#
#     # 2️⃣ Plan mavjudligini tekshir
#     plans = Plan.objects.filter(
#         organization=organization,
#         statement=statement
#     ).only("id")
#
#     if not plans.exists():
#         print("❌ Plan not found for this statement and organization.")
#         raise _raise_missing_plan_error(plan_columns)
#
#     # 3️⃣ PlanItem larni yuklash
#     plan_items = PlanItem.objects.filter(
#         plan__in=plans,
#         column__in=plan_columns
#     ).select_related("column")
#
#     if not plan_items.exists():
#         print("❌ No PlanItems at all.")
#         raise _raise_missing_plan_error(plan_columns)
#
#     # 4️⃣ Foydali PlanItem bormi?
#     # usable_items = [item for item in plan_items if not _is_empty_plan_value(item.plan_value)]
#     plan_items = PlanItem.objects.filter(
#         plan__in=plans,
#         column__in=plan_columns
#     ).select_related("column")
#     if not plan_items.exists():
#         print("❌ No PlanItems at all.")
#         raise _raise_missing_plan_error(plan_columns)
#
#     print("✅ [DONE] At least one usable plan item exists.")
#
#
# def _raise_missing_plan_error(missing_columns):
#     """Xatolik chiqarish"""
#     cols_str = ", ".join(f"{c.ordering} – {getattr(c, 'title_uz', c.title)}" for c in missing_columns)
#     msg = _(
#         "Bu hisobot uchun reja kiritilmagan. "
#         "Quyidagi ustunlar bo‘yicha reja (plan) mavjud emas yoki 0 ga teng."
#         "Iltimos, bo‘lim administratori avval reja kiritgandan so‘ng hisobot yarating."
#     ) % {"cols": cols_str}
#     raise serializers.ValidationError({"non_field_errors": [msg]})
