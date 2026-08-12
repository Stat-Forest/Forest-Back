# apps/reports/services/plan_columns.py
"""
Har bir Statement (bo'lim) o'zining tartibida qaysi ustunlarni foydalanuvchidan
kiritishini belgilaydigan umumiy funksiya.

MUHIM: bu logika avval faqat `PlanStatementColumnListAPIView.filter_queryset`
ichida (frontend uchun) yozilgan edi. Endi shu funksiya orqali chaqiriladi —
shunda frontend column-list API'si bilan Excel shablon/import bir xil
mantiqdan foydalanadi va kelajakda ikkalasi bir-biridan farq qilib
qolmaydi.

Foydalanish:
    columns = get_plan_input_columns(statement)   # ordered queryset

`PlanStatementColumnListAPIView`ni ham shu funksiyaga o'tkazib qo'yishni
tavsiya qilaman (pastda misolda ko'rsatilgan), lekin bu fayl mustaqil ham
ishlaydi.
"""

from django.db.models import Q, IntegerField, Value, CharField
from django.db.models.functions import Cast, Concat
from django.db.models.expressions import Func

from apps.reports.models import StatementColumn
from apps.utils.services.variables import (
    MONTHLY_STATUSES,
    QUARTERLY_STATUSES,
    YEARLY_STATUSES,
    YEARLY_TOTAL_STATUSES,
)

# YILLIK_1 / YILLIK_2 / YILLIK_3 kodlari StatementColumn.PlanStatus da bo'lishi kerak,
# lekin ba'zi joylarda literal string sifatida ham ishlatilgan (plan.py serializer),
# shuning uchun bu yerda ham literal qoldiraman — moslik uchun.
YILLIK_1 = "yillik_1"
YILLIK_2 = "yillik_2"
YILLIK_3 = "yillik_3"
YILLIK = "yillik"


class SplitPart(Func):
    """PostgreSQL SPLIT_PART() wrapper — 'ordering' maydonini bo'lib olish uchun."""
    function = "SPLIT_PART"
    arity = 3


def get_plan_input_columns(statement, base_qs=None):
    """
    Berilgan statement uchun foydalanuvchi TO'LDIRISHI kerak bo'lgan
    StatementColumn'larni (leaf-level, status_plan bilan) tartiblab qaytaradi.

    Ustuvorlik (statement'dagi mavjud status_plan'larga qarab):
        1) Oylik ustunlar mavjud bo'lsa -> faqat oylik ustunlar
        2) Aks holda choraklik mavjud bo'lsa -> faqat choraklik
        3) Aks holda yillik (yoki YILLIK_1/YILLIK_2) mavjud bo'lsa -> shular
           (agar YILLIK_1/YILLIK_2 bo'lsa, YILLIK_3 chiqarilmaydi — u avtomatik hisoblanadi)
        4) Aks holda faqat YILLIK_TOTAL mavjud bo'lsa -> shu

    Natija `ordering` maydoni bo'yicha (parent ierarxiyasi + oxirgi raqam)
    saralanadi — shu bilan har bir bo'lim o'z tartibida chiqadi.
    """
    qs = base_qs if base_qs is not None else StatementColumn.objects.filter(statement=statement)
    qs = qs.filter(Q(parent__isnull=False) & Q(status_plan__isnull=False))

    existing_statuses = set(qs.values_list("status_plan", flat=True))

    if YILLIK_1 in existing_statuses or YILLIK_2 in existing_statuses:
        filtered_yearly_statuses = {YILLIK_1, YILLIK_2, YILLIK}
    else:
        filtered_yearly_statuses = YEARLY_STATUSES

    if existing_statuses.intersection(MONTHLY_STATUSES):
        qs = qs.filter(status_plan__in=MONTHLY_STATUSES)
    elif existing_statuses.intersection(QUARTERLY_STATUSES):
        qs = qs.filter(status_plan__in=QUARTERLY_STATUSES)
    elif existing_statuses.intersection(YEARLY_STATUSES):
        qs = qs.filter(status_plan__in=filtered_yearly_statuses)
    elif existing_statuses.intersection(YEARLY_TOTAL_STATUSES):
        qs = qs.filter(status_plan__in=YEARLY_TOTAL_STATUSES)
    else:
        return qs.none()

    qs = qs.annotate(
        parent_full_title=Concat(
            "parent__parent__parent__parent__parent__title_uz", Value(" - "),
            "parent__parent__parent__parent__title_uz", Value(" - "),
            "parent__parent__parent__title_uz", Value(" - "),
            "parent__parent__title_uz", Value(" - "),
            "parent__title_uz",
            output_field=CharField(),
        )
    ).annotate(
        last_num=Cast(SplitPart("ordering", Value("."), Value(-1)), IntegerField()),
    ).select_related(
        "parent", "parent__parent", "parent__parent__parent",
        "parent__parent__parent__parent", "parent__parent__parent__parent__parent",
    ).order_by("parent_full_title", "last_num")

    return qs