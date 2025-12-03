from decimal import Decimal

from apps.reports.models import Deadline


def get_or_create_general_report(statement, deadline, region=None):
    """
    Regional (viloyat) jami reportini deadline-dan mustaqil tarzda bitta qilib yuritadi.
    - Unikal kalit: (statement, region, is_general=True, organization=NULL)
    - Ichkarida so‘nggi (latest) Deadline tanlanadi va report shu deadline bilan bog‘lanadi.
    - Agar bir nechta nusxa bo‘lsa, eng yangisi qoladi, qolganlari o‘chiriladi.
    """
    from apps.reports.models import Report

    # 1) Mazkur region uchun so'nggi deadline-ni aniqlash
    latest_deadline = (
        Deadline.objects.filter(statement=statement, organizations__region=region)
        .order_by('-created_at')
        .first()
    )
    # Fallback: agar region bo'yicha deadline topilmasa, statement bo'yicha eng so'nggi deadline-ni olamiz
    if not latest_deadline:
        latest_deadline = (
            Deadline.objects.filter(statement=statement)
            .order_by('-created_at')
            .first()
        )

    # Agar deadline topilmasa ham obyekt mavjud bo'lishi kerak, ammo deadline-ni None
    # qilish o‘rniga, mavjud bo‘lsa saqlaymiz. Aggregation funktsiyalari o‘zlari
    # latest_deadline bilan ishlaydi.

    # 2) Mavjud jami report(lar)ni deadline-dan qat'i nazar qidiramiz
    qs = Report.objects.filter(
        organization__isnull=True,
        statement=statement,
        is_general=True,
        region=region,
    ).order_by('-created_at')

    general_report = qs.first()

    # 3) Dublikatlar bo‘lsa, barchasini birga yig‘amiz va bitta qoldiramiz
    if qs.count() > 1:
        keep_id = general_report.id
        qs.exclude(id=keep_id).delete()

    # 4) Agar yo‘q bo‘lsa – yaratamiz
    if not general_report:
        general_report = Report.objects.create(
            organization=None,
            statement=statement,
            deadline=latest_deadline,
            is_general=True,
            region=region,
            status=Report.StatusChoices.SAVED,
            is_report=False,
        )
    else:
        # 5) Mavjud bo‘lsa – deadline-ni eng songgisiga yangilaymiz
        if latest_deadline and general_report.deadline_id != getattr(latest_deadline, 'id', None):
            general_report.deadline = latest_deadline
            general_report.save(update_fields=['deadline'])

    # 6) sent_by_role ni konsistent saqlaymiz
    if region:
        if general_report.sent_by_role != f"region:{region}":
            general_report.sent_by_role = f"region:{region}"
            general_report.save(update_fields=["sent_by_role"])

    # 7) Flaglarni kafolatlaymiz
    updates = {}
    if general_report.is_report:
        updates['is_report'] = False
    if general_report.status != Report.StatusChoices.SAVED:
        updates['status'] = Report.StatusChoices.SAVED
    if updates:
        for k, v in updates.items():
            setattr(general_report, k, v)
        general_report.save(update_fields=list(updates.keys()))

    return general_report


def get_or_create_national_report(statement, deadline, region=None):
    """
    Respublika jami reportini deadline-dan mustaqil tarzda bitta qilib yuritadi.
    - Unikal kalit: (statement, is_republic=True) [region odatda RegionChoices.REPUBLIC]
    - Ichkarida so‘nggi (latest) Deadline tanlanadi va report shu deadline bilan bog‘lanadi.
    - Agar bir nechta nusxa bo‘lsa, eng yangisi qoladi, qolganlari o‘chiriladi.
    """
    from apps.reports.models import Report

    # 1) So'nggi deadline-ni aniqlash (respublika umumiy, statement bo‘yicha)
    latest_deadline = (
        Deadline.objects.filter(statement=statement)
        .order_by('-created_at')
        .first()
    )

    # 2) Mavjud respublika jami report(lar)ni deadline-dan qat'i nazar qidiramiz
    qs = Report.objects.filter(
        statement=statement,
        is_republic=True,
    ).order_by('-created_at')

    national_report = qs.first()

    # 3) Dublikatlar bo‘lsa – bitta qoldiramiz
    if qs.count() > 1:
        keep_id = national_report.id
        qs.exclude(id=keep_id).delete()

    # 4) Agar yo‘q bo‘lsa – yaratamiz
    if not national_report:
        national_report = Report.objects.create(
            statement=statement,
            deadline=latest_deadline,
            is_republic=True,
            region=region,
            status=Report.StatusChoices.SAVED,
            is_report=False,
        )
    else:
        # 5) Mavjud bo‘lsa – deadline-ni eng songgisiga yangilaymiz
        if latest_deadline and national_report.deadline_id != getattr(latest_deadline, 'id', None):
            national_report.deadline = latest_deadline
            national_report.save(update_fields=['deadline'])

    # 6) sent_by_role ni konsistent saqlaymiz
    if region:
        desired = f"national:{region}"
        if national_report.sent_by_role != desired:
            national_report.sent_by_role = desired
            national_report.save(update_fields=["sent_by_role"])

    # 7) Flaglarni kafolatlaymiz
    updates = {}
    if national_report.is_report:
        updates['is_report'] = False
    if national_report.status != Report.StatusChoices.SAVED:
        updates['status'] = Report.StatusChoices.SAVED
    if updates:
        for k, v in updates.items():
            setattr(national_report, k, v)
        national_report.save(update_fields=list(updates.keys()))

    return national_report


def normalize(value):
    if value is None:
        return Decimal(0)
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal(0)


def aggregate_national_report(statement, deadline, region):
    from collections import defaultdict
    from apps.utils.services.is_that_number import safe_decimal
    from apps.reports.models import Report, ReportItem, ReportItemInner

    # 1️⃣ Oxirgi deadline-ni topamiz (faqat parent report uchun, yig'ish deadline-dan mustaqil)
    latest_deadline = Deadline.objects.filter(
        statement=statement
    ).order_by('-created_at').first()

    if not latest_deadline:
        print("❌ [REPUBLIC] Deadline topilmadi")
        return None

    deadline = latest_deadline

    # 1️⃣ Regional umumiy (is_general=True) reportlarni olamiz — deadline cheklovisiz
    general_reports = Report.objects.filter(
        statement=statement,
        is_general=True,
        status=Report.StatusChoices.SAVED
    )
    if not general_reports.exists():
        print("❌ [REPUBLIC] Hech qanday viloyat Jami topilmadi")
        return None

    # 2️⃣ Respublika Jami reportini olamiz yoki yaratamiz
    national_report = get_or_create_national_report(statement, deadline, region)

    print(f"✅ [REPUBLIC] Report ID: {national_report.id}")

    # 3️⃣ Eski item va innerlarni tozalaymiz
    ReportItem.objects.filter(report=national_report).delete()

    # 4️⃣ Barcha viloyat jami item va innerlarni olamiz
    all_items = (
        ReportItem.objects
        .filter(report__in=general_reports)
        .select_related("statement_column")
        .prefetch_related("inners")
    )

    # 5️⃣ column_id -> value list bo‘yicha yagona qiymatlarni hisoblaymiz
    grouped_values = defaultdict(list)
    for item in all_items:
        for inner in item.inners.all():
            grouped_values[item.statement_column_id].append(inner.value)

    # 6️⃣ Yangi ReportItem larni yaratamiz (faqat yagona column_id lar bilan)
    new_inners = []

    for column_id, values in grouped_values.items():
        item = ReportItem.objects.create(
            report=national_report,
            statement_column_id=column_id
        )
        total = sum(safe_decimal(v) for v in values)
        new_inners.append(ReportItemInner(report_item=item, value=str(total)))

    ReportItemInner.objects.bulk_create(new_inners)

    print(f"📊 {len(new_inners)} ta inner yozildi.")

    return national_report


def aggregate_general_report(statement, deadline, region):
    from decimal import Decimal
    from apps.utils.services.is_that_number import safe_decimal
    from apps.reports.models import Report, ReportItem, ReportItemInner

    latest_deadline = Deadline.objects.filter(
        statement=statement,
        organizations__region=region
    ).order_by('-created_at').first()

    if not latest_deadline:
        print("❌ [GENERAL] Deadline topilmadi")
        return None

    deadline = latest_deadline

    # 🔁 1. Avval viloyat Jami (general) report obyektini olamiz
    general_report = get_or_create_general_report(statement, deadline, region)
    if not general_report:
        return None

    # 🔄 2. Avvalgi ma’lumotlarni tozalaymiz
    ReportItem.objects.filter(report=general_report).delete()

    # 🔎 3. Manba: ACCEPTED individual reportlar (bevosita asosiy manba)
    regional_reports = (
        Report.objects.filter(
            statement=statement,
            is_general=False,
            is_republic=False,
            is_report=True,
            status=Report.StatusChoices.ACCEPTED,
            region=region,
        ).select_related("organization__republic")
    )

    # Parent general reportning deadline'i serializerdagi filterga mos kelishi uchun
    # bolalar orasidagi eng so'nggi deadline bilan sinxronlaymiz.
    if regional_reports.exists():
        latest_child = regional_reports.order_by('-deadline__created_at').first()
        if latest_child and general_report.deadline_id != getattr(latest_child.deadline, 'id', None):
            general_report.deadline = latest_child.deadline
            general_report.save(update_fields=['deadline'])

    all_items = ReportItem.objects.filter(
        report__in=regional_reports
    ).select_related("statement_column").prefetch_related("inners")

    from collections import defaultdict
    column_total_map = defaultdict(Decimal)
    touched_column_ids = set()

    for item in all_items:
        col_id = item.statement_column_id
        touched_column_ids.add(col_id)
        for inner in item.inners.all():
            column_total_map[col_id] += safe_decimal(inner.value)

    # 🧾 4. Yangi ReportItem va ReportItemInner yaratish
    new_items = [
        ReportItem(report=general_report, statement_column_id=col_id)
        for col_id in touched_column_ids
    ]
    ReportItem.objects.bulk_create(new_items)

    created_items = ReportItem.objects.filter(
        report=general_report,
        statement_column_id__in=touched_column_ids
    )

    all_inners = [
        ReportItemInner(
            report_item=item,
            value=str(column_total_map.get(item.statement_column_id, Decimal(0)))
        )
        for item in created_items
    ]
    ReportItemInner.objects.bulk_create(all_inners)

    return general_report