# apps/reports/services/report_import/plan_validation.py
"""
Import qilinayotgan Excel faylida "Reja" (`StatementColumn.status_plan`
berilgan) ustunlarga tegishli qiymatlar uchrasa, ular bo'lim_admin
tomonidan tasdiqlangan Plan/PlanItem (yoki plantlik reja bo'lsa
PlantPlan/PlantPlanItem) qiymati bilan bir xil bo'lishi SHART.

Nega kerak: Reja qiymatlarini FAQAT bo'lim_admin `PlanCreateView` /
`PlanExcelImportAPIView` orqali kiritadi (`apps/reports/views/plan/`,
`apps/reports/services/plan_excel.py`). Import-parse Reja ustunlarini
hech qachon saqlamaydi — faqat "Amalda" ustunlar qaytariladi
(`columns.get_importable_columns` Reja ustunlarni istisno qiladi).
Ammo foydalanuvchi yuklagan `.xlsx` fayl (masalan eski eksport yoki
qo'lda tuzilgan fayl) Reja ustunlariga mos sarlavha va qiymatlarni ham
o'z ichiga olishi mumkin. Bu qiymatlar rasman tasdiqlangan Reja bilan
mos kelmasa — foydalanuvchi eskirgan/boshqa davrga tegishli fayldan
foydalanayotganining alomati, shuning uchun butun import rad etiladi
(faylni Amalda qismini ham qisman qabul qilib bo'lmaydi — yagona,
tushunarli xatolik bilan orqaga qaytariladi).
"""

from decimal import Decimal, InvalidOperation

from apps.reports.models import Plan, PlanItem, PlantPlan, PlantPlanItem
from apps.reports.services.report_import.columns import _issue, normalize_title

# Decimal(30, 2) saqlanadigan reja qiymati bilan Excel'dan o'qilgan matn
# orasidagi formatlash farqlarini (masalan "100" vs "100.00") yutish uchun.
TOLERANCE = Decimal("0.01")


class PlanMismatchError(ValueError):
    """
    Faylda topilgan Reja qiymati tasdiqlangan Plan/PlanItem bilan mos
    kelmasa (yoki reja umuman hali tasdiqlanmagan bo'lsa) ko'tariladi.

    `issues` — `_issue()` shaklidagi ro'yxat, view buni to'g'ridan-to'g'ri
    javobning `errors` maydoniga qo'yadi.
    """

    def __init__(self, message, issues):
        super().__init__(message)
        self.issues = issues


def _to_decimal(value):
    if value is None:
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _values_match(excel_value, plan_value):
    excel_dec = _to_decimal(excel_value)
    plan_dec = _to_decimal(plan_value)
    if excel_dec is not None and plan_dec is not None:
        return abs(excel_dec - plan_dec) <= TOLERANCE
    # Raqam bo'lmagan reja ustuni bo'lsa (kamdan-kam) — matn sifatida solishtiramiz.
    return normalize_title(excel_value) == normalize_title(plan_value)


def _format_expected(value):
    if isinstance(value, Decimal):
        normalized = value.normalize()
        return format(normalized, "f")
    return str(value)


def validate_plan_values(*, statement, organization, year, season, index_label,
                          flat_found, plant_found):
    """
    Faylda topilgan Reja qiymatlarini (`flat_found`/`plant_found`)
    tasdiqlangan Plan bilan solishtiradi. Hech narsa topilmagan bo'lsa
    (fayl Reja ustunlarini umuman o'z ichiga olmagan — odatiy holat)
    darhol jim chiqib ketadi — bu tekshiruv faqat fayl Reja qiymatlarini
    HAQIQATDA o'z ichiga olganda ishga tushadi.

    Args:
        statement: Statement instance ("bo'lim" — Plan.statement)
        organization: Organization instance yoki UUID/pk
        year: int
        season: str|None — Plan.SeasonChoices qiymati
        index_label: column_id(str) -> ko'rsatiladigan nom (StatementColumnIndex.label)
        flat_found: {column_id: (value, row)} — oddiy (yoki plantlik report
            ustidagi flat reja) uchun fayldan topilgan qiymatlar
        plant_found: {plant_id: {column_id: (value, row)}} — plantlik reja
            (PlantPlanItem) bilan solishtirish uchun, o'simlik bo'yicha

    Raises:
        PlanMismatchError — reja hali tasdiqlanmagan yoki qiymatlar mos kelmasa.
    """
    if not flat_found and not plant_found:
        return

    plan_filters = {"organization": organization, "statement": statement, "year": year}
    if season:
        plan_filters["season"] = season
    else:
        plan_filters["season__isnull"] = True

    plan = Plan.objects.filter(**plan_filters).first()

    if plan is None:
        issues = _missing_plan_issues(flat_found, plant_found, index_label)
        raise PlanMismatchError(
            "Faylda reja (status_plan) ustunlariga qiymat kiritilgan, lekin "
            "bu tashkilot/yil uchun hali bo'lim admin tomonidan tasdiqlangan "
            "reja topilmadi. Import rad etildi.",
            issues,
        )

    has_plant_plan = PlantPlan.objects.filter(plan=plan).exists()

    issues = []

    if has_plant_plan:
        expected = {
            (str(item.plant_plan.plant_id), str(item.column_id)): item.plan_value
            for item in PlantPlanItem.objects.filter(plant_plan__plan=plan)
            .select_related("plant_plan")
        }
    else:
        expected = {
            str(item.column_id): item.plan_value
            for item in PlanItem.objects.filter(plan=plan)
        }

    for column_id, (value, row) in flat_found.items():
        exp = expected.get(column_id)
        if exp is None:
            continue  # bu ustun uchun reja umuman kiritilmagan — jim o'tamiz
        if not _values_match(value, exp):
            issues.append(_mismatch_issue(index_label, column_id, value, exp, row))

    for plant_id, cols in plant_found.items():
        for column_id, (value, row) in cols.items():
            key = (plant_id, column_id) if has_plant_plan else column_id
            exp = expected.get(key)
            if exp is None:
                continue
            if not _values_match(value, exp):
                issues.append(_mismatch_issue(index_label, column_id, value, exp, row))

    if issues:
        raise PlanMismatchError(
            "Faylda reja ustunlariga kiritilgan qiymatlar bo'lim admin "
            "tasdiqlagan reja bilan mos kelmadi. Import rad etildi.",
            issues,
        )


def _mismatch_issue(index_label, column_id, excel_value, expected_value, row):
    title = index_label(column_id)
    return _issue(
        f"«{title}» — faylda kiritilgan qiymat ({excel_value}) tasdiqlangan "
        f"reja qiymatidan ({_format_expected(expected_value)}) farq qiladi.",
        row=row,
        column_title=title,
    )


def _missing_plan_issues(flat_found, plant_found, index_label):
    issues = []
    for column_id, (value, row) in flat_found.items():
        title = index_label(column_id)
        issues.append(_issue(
            f"«{title}» — reja ustuniga qiymat kiritilgan, lekin bu "
            f"tashkilot/yil uchun hali tasdiqlangan reja mavjud emas.",
            row=row, column_title=title,
        ))
    for cols in plant_found.values():
        for column_id, (value, row) in cols.items():
            title = index_label(column_id)
            issues.append(_issue(
                f"«{title}» — reja ustuniga qiymat kiritilgan, lekin bu "
                f"tashkilot/yil uchun hali tasdiqlangan reja mavjud emas.",
                row=row, column_title=title,
            ))
    return issues
