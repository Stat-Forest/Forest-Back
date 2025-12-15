from collections import defaultdict
from apps.utils.services.is_that_number import is_number


def get_year_from_deadline(deadline):
    """
    Deadline.submit_at dan YYYY ni ajratib olish
    """
    if not deadline.submit_at:
        raise ValueError("Deadline.submit_at is empty")
    year_str = str(deadline.submit_at).strip().split("-")[0]
    return int(year_str)


def aggregate_individual_report(source_report):
    from decimal import Decimal
    from apps.reports.models import (
        Report, ReportItem, ReportItemInner,
        PlanItem, StatementColumn
    )

    # 1️⃣ Eski tashkilot jami reportni tozalaymiz
    Report.objects.filter(
        organization=source_report.organization,
        statement=source_report.statement,
        deadline=source_report.deadline,
        is_individual_general=True
    ).delete()

    # 2️⃣ Tashkilot jami reportni yaratamiz
    region = source_report.organization.region if source_report.organization else source_report.region
    republic = source_report.organization.republic if source_report.organization else source_report.republic

    individual_report = Report.objects.create(
        organization=source_report.organization,
        statement=source_report.statement,
        deadline=source_report.deadline,
        status=Report.StatusChoices.SAVED,
        is_general=False,
        is_individual_general=True,
        is_report=False,
        region=region,
        republic=republic,
    )

    # 3️⃣ Hammasi uchun ReportItem tayyorlab olish uchun qiymatlar yig‘amiz
    column_values_map = defaultdict(list)
    all_items = source_report.report_items.prefetch_related("inners")

    for item in all_items:
        for inner in item.inners.all():
            column_values_map[item.statement_column_id].append(inner.value)

    # 🌱 Urug' xarakati Reja bo'lsa, FOIZ ustunini ham majburan qo'shamiz (agar yo'q bo'lsa)
    is_seed_statement = source_report.statement.name_uz.strip() == "Urug' xarakati Reja"
    if is_seed_statement:
        foiz_col = StatementColumn.objects.filter(
            statement=source_report.statement,
            ordering="1.1.2.3"
        ).first()
        if foiz_col and foiz_col.id not in column_values_map:
            # Bo'sh ro'yxat qo'shamiz — keyinroq qiymat "0" beriladi
            column_values_map[foiz_col.id] = []

    # 4️⃣ Yangi itemlar va ularning qiymatlarini bulk yaratamiz
    new_items = []
    new_inners = []

    for column_id, values in column_values_map.items():
        report_item = ReportItem(
            report=individual_report,
            statement_column_id=column_id
        )
        new_items.append(report_item)

        # 🌱 Urug' xarakati Reja uchun maxsus: REJA (1.1.2.1) PlanItem dan, FOIZ (1.1.2.3) = "0"
        if is_seed_statement:
            is_reja_column = StatementColumn.objects.filter(
                id=column_id,
                ordering="1.1.2.1"
            ).exists()
            is_foiz_column = StatementColumn.objects.filter(
                id=column_id,
                ordering="1.1.2.3"
            ).exists()

            if is_reja_column:
                plan_year = get_year_from_deadline(source_report.deadline)
                plan_value = PlanItem.objects.filter(
                    plan__statement=source_report.statement,
                    plan__organization=source_report.organization,
                    plan__year=plan_year,
                    column_id=column_id
                ).values_list("plan_value", flat=True).first() or Decimal("0.0")
                value = str(plan_value)
            elif is_foiz_column:
                # FOIZni boshlang'ich 0 qilib qo'yamiz; keyin seed_movement_plan hisoblaydi
                value = "0"
            else:
                # Masalan AMALDA ustuni: numeric summasi
                numeric_values = [Decimal(str(v)) for v in values if is_number(v)]
                value = str(sum(numeric_values)) if numeric_values else "0"
        else:
            # Boshqa barcha statementlar uchun eski xulq
            numeric_values = [Decimal(str(v)) for v in values if is_number(v)]
            value = str(sum(numeric_values)) if numeric_values else "0"

        new_inners.append(
            ReportItemInner(report_item=report_item, value=value)
        )

    # 5️⃣ Bulk create
    ReportItem.objects.bulk_create(new_items)
    ReportItemInner.objects.bulk_create(new_inners)

    # 6️⃣ Agar Urug' xarakati Reja bo'lsa, FOIZni darhol hisoblaymiz (inline)
    if is_seed_statement:
        from decimal import Decimal
        from apps.reports.services.get_two_numbers_in_percent import round_decimal
        # StatementColumn ordering larini aniqlaymiz
        reja_col = StatementColumn.objects.filter(
            statement=source_report.statement,
            ordering="1.1.2.1",
        ).first()
        amalda_col = StatementColumn.objects.filter(
            statement=source_report.statement,
            ordering="1.1.2.2",
        ).first()
        foiz_col = StatementColumn.objects.filter(
            statement=source_report.statement,
            ordering="1.1.2.3",
        ).first()

        if reja_col and amalda_col and foiz_col:
            items = individual_report.report_items.prefetch_related("inners")
            item_map = {i.statement_column_id: i for i in items}

            reja_item = item_map.get(reja_col.id)
            amalda_item = item_map.get(amalda_col.id)
            foiz_item = item_map.get(foiz_col.id)

            def _norm(v):
                try:
                    return Decimal(str(v))
                except Exception:
                    return Decimal("0")

            # REJA org-level
            reja_val = Decimal("0")
            if reja_item:
                org_inner = reja_item.inners.filter(plant__isnull=True).first()
                if org_inner:
                    reja_val = _norm(org_inner.value)

            # AMALDA org-level yoki plant yig'indisi
            amalda_val = Decimal("0")
            if amalda_item:
                org_inn = amalda_item.inners.filter(plant__isnull=True).first()
                if org_inn:
                    amalda_val = _norm(org_inn.value)
                else:
                    for inn in amalda_item.inners.all():
                        if inn.plant_id:
                            amalda_val += _norm(inn.value)

            # FOIZni yozamiz (faqat org-level)
            if foiz_item:
                target = foiz_item.inners.filter(plant__isnull=True).first()
                if not target:
                    from apps.reports.models import ReportItemInner
                    target = ReportItemInner.objects.create(report_item=foiz_item, value="0")

                foiz_val = round_decimal((amalda_val / reja_val * 100) if reja_val else Decimal("0"))
                if str(foiz_val) != target.value:
                    target.value = str(foiz_val)
                    target.save(update_fields=["value"])

        # Ikkinchi safety net sifatida mavjud hisoblagichni ham chaqiramiz
        from apps.reports.report_calculate.forest_create.seed_movement_plan import (
            calculate_seed_movement_plan,
        )
        try:
            calculate_seed_movement_plan(individual_report)
        except Exception:
            pass

    return individual_report
