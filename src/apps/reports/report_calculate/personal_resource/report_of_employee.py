from apps.utils.report_math import sum_values
from apps.reports.models import ReportItem, Report, ReportItemInner


def create_calculated_item(report, column, value):
    item = ReportItem.objects.create(
        report=report,
        statement_column=column
    )
    ReportItemInner.objects.create(
        report_item=item,
        value=str(value)
    )


def calculate_hodimlar_hisobi(report: Report):
    statement = report.statement
    columns = statement.columns.prefetch_related("children").all()

    col_map = {}
    for col in columns:
        if col.title_uz:
            col_map[col.title_uz.strip()] = col
        if col.title_ru:
            col_map[col.title_ru.strip()] = col

    def get_cols(names):
        return [col_map[name] for name in names if name in col_map]

    # === 1. Jami xodimlar soni (faqat shundan-1 ichidagi ustunlar!)
    shundan_1_names = [
        "Boshqaruv xodimlari", "Руководящие работники",
        "Mutaxassislar", "Специалисты",
        "Ishlab chiqarish xodimlari", "Производственные работники",
        "Texnik hodim", "Технический персонал",
        "Xizmat korsatuvchi xodimlar", "Обслуживающий персонал",
        "ishchilar", "Рабочие"
    ]

    # Top parent: "Shundan-1"
    shundan_1_parent = None
    for name in ["Shundan-1", "Из них-1"]:
        if name in col_map:
            shundan_1_parent = col_map[name]
            break

    if shundan_1_parent:
        # Tanlangan faqat shundan-1 ichidagi kerakli ustunlar
        valid_children = {
            c.title_uz.strip(): c for c in shundan_1_parent.children.all() if c.title_uz
        }
        valid_children.update({
            c.title_ru.strip(): c for c in shundan_1_parent.children.all() if c.title_ru
        })

        columns_to_sum = []
        for name in shundan_1_names:
            if name in valid_children:
                columns_to_sum.append(valid_children[name])

        jami_xodimlar_soni = sum_values(report, columns_to_sum)
        for name in ["Jami xodimlar soni", "Общее количество сотрудников"]:
            if name in col_map:
                create_calculated_item(report, col_map[name], jami_xodimlar_soni)
                break

    # === 2. Jami vakansiyalar soni (shundan-2 ichidan olish kerak)
    jami_vakansiyalar_soni = sum_values(report, get_cols([
        "Boshqaruv hodimlari", "Руководящие работники",
        "Mutaxassislar", "Специалисты",
        "Ishlab chiqarish xodimlari", "Производственные работники",
        "Texnik xodim", "Технический персонал",
        "Xizmat korsatuvchi xodimlar", "Обслуживающий персонал",
        "Ishchilar", "Рабочие"
    ]))
    for name in ["Jami vakatlar soni", "Общее количество вакансий"]:
        if name in col_map:
            create_calculated_item(report, col_map[name], jami_vakansiyalar_soni)
            break

    # === 3. Jami ishlovchi xodimlar soni (ma'lumot darajasi bo‘yicha)
    jamisi_malumot = sum_values(report, get_cols([
        "Oliy", "Высшее",
        "O'rta maxsus", "Среднее специальное",
        "O'rta", "Среднее"
    ]))
    for name in ["Jami ishlovchi xodimlar soni", "Общее количество работающих сотрудников"]:
        if name in col_map:
            create_calculated_item(report, col_map[name], jamisi_malumot)
            break

    # === 4. Jami yangi yaratilgan ish o‘rinlar soni
    jami_yangi_ish_orni = sum_values(report, get_cols([
        "Doimiy", "Постоянные",
        "Mavsumiy", "Сезонные"
    ]))
    for name in ["Jami yangi yaratilgan ish o'rinlar soni", "Общее количество новых рабочих мест"]:
        if name in col_map:
            create_calculated_item(report, col_map[name], jami_yangi_ish_orni)
            break
