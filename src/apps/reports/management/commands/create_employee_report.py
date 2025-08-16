from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices

class Command(BaseCommand):
    help = "Create Statement Column for Hodim Hisobi with multilingual titles"

    def handle(self, *args, **options):

        def create_statement(parent, name_uz, name_ru, period=None):
            return Statement.objects.create(
                parent=parent,
                name=name_uz,
                name_uz=name_uz,
                name_ru=name_ru,
                period=period
            )

        def create_column(statement, parent, title_uz, title_ru, ordering, is_organization=False, is_user_input=True):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title=title_uz,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=ordering,
                is_organization=is_organization,
                is_user_input=is_user_input
            )

        # === Root Statements ===
        person_statement = create_statement(
            parent=None,
            name_uz="Insoniyat resurslarini boshqarish",
            name_ru="Управление человеческими ресурсами"
        )

        person_report_statement = create_statement(
            parent=person_statement,
            name_uz="Xodimlar hisobi",
            name_ru="Учёт сотрудников",
            period=PeriodChoices.CHORAKLIK
        )

        # === 1-Ilova ===
        ilova1 = create_column(person_report_statement, None, "1-ilova", "Приложение 1", "1.1")

        title_col = create_column(person_report_statement, ilova1,
                                  "2025 yil uchun xodimlar togrisidagi hisobat",
                                  "Отчёт о сотрудниках за 2025 год",
                                  "1.1.1")

        create_column(person_report_statement, title_col, "Tashkilot nomi", "Название организации", "1.1.1.1", is_organization=True)
        create_column(person_report_statement, title_col, "Jami xodimlar soni", "Общее количество сотрудников", "1.1.1.2")

        shundan1 = create_column(person_report_statement, title_col, "Shundan-1", "Из них-1", "1.1.1.3")
        create_column(person_report_statement, shundan1, "Boshqaruv xodimlari", "Руководящие работники", "1.1.1.3.1")
        create_column(person_report_statement, shundan1, "Mutaxassislar", "Специалисты", "1.1.1.3.2")
        create_column(person_report_statement, shundan1, "Ishlab chiqarish xodimlari", "Производственные работники", "1.1.1.3.3")
        create_column(person_report_statement, shundan1, "Texnik hodim", "Технический персонал", "1.1.1.3.4")
        create_column(person_report_statement, shundan1, "Xizmat korsatuvchi xodimlar", "Обслуживающий персонал", "1.1.1.3.5")
        create_column(person_report_statement, shundan1, "ishchilar", "Рабочие", "1.1.1.3.6")

        create_column(person_report_statement, title_col, "Jami vakatlar soni", "Общее количество вакансий", "1.1.1.4")

        shundan2 = create_column(person_report_statement, title_col, "shundan-2", "Из них-2", "1.1.1.5")
        create_column(person_report_statement, shundan2, "Boshqaruv hodimlari", "Руководящие работники", "1.1.1.5.1")
        create_column(person_report_statement, shundan2, "Mutaxassislar", "Специалисты", "1.1.1.5.2")
        create_column(person_report_statement, shundan2, "Ishlab chiqarish xodimlari", "Производственные работники", "1.1.1.5.3")
        create_column(person_report_statement, shundan2, "Texnik xodim", "Технический персонал", "1.1.1.5.4")
        create_column(person_report_statement, shundan2, "Xizmat korsatuvchi xodimlar", "Обслуживающий персонал", "1.1.1.5.5")
        create_column(person_report_statement, shundan2, "Ishchilar", "Рабочие", "1.1.1.5.6")

        # === 2-Ilova ===
        ilova2 = create_column(person_report_statement, None, "2-ilova", "Приложение 2", "1.2")

        title2 = create_column(person_report_statement, ilova2,
                               "Tizim tashkilotlaridagi xodimlarni sifat tarkibi togrisida malumot",
                               "Информация о качественном составе сотрудников",
                               "1.2.1")

        create_column(person_report_statement, title2, "Tashkilot nomi", "Название организации", "1.2.1.1", is_organization=True)
        create_column(person_report_statement, title2, "Shtat bo'yicha jami", "Всего по штату", "1.2.1.2")
        create_column(person_report_statement, title2, "Jami ishlovchi xodimlar soni", "Общее количество работающих сотрудников", "1.2.1.3")

        malumoti = create_column(person_report_statement, title2, "Ma'lumoti", "Образование", "1.2.1.4")
        create_column(person_report_statement, malumoti, "Oliy", "Высшее", "1.2.1.4.1")
        create_column(person_report_statement, malumoti, "O'rta maxsus", "Среднее специальное", "1.2.1.4.2")
        create_column(person_report_statement, malumoti, "O'rta", "Среднее", "1.2.1.4.3")

        xodimlar = create_column(person_report_statement, title2, "Xodimlar", "Сотрудники", "1.2.1.5")
        create_column(person_report_statement, xodimlar, "Ayol", "Женщины", "1.2.1.5.1")
        create_column(person_report_statement, xodimlar, "Erkak xodimlar", "Мужчины", "1.2.1.5.2")
        create_column(person_report_statement, xodimlar, "Yoshlar Jami", "Всего молодёжи", "1.2.1.5.3")

        yoshlar = create_column(person_report_statement, xodimlar, "Yoshlar", "Молодёжь", "1.2.1.5.4")
        create_column(person_report_statement, yoshlar, "Qizlar", "Девушки", "1.2.1.5.4.1")
        create_column(person_report_statement, yoshlar, "Yigitlar", "Юноши", "1.2.1.5.4.2")

        create_column(person_report_statement, xodimlar, "Nafaqadagi xodimlar", "Пенсионеры", "1.2.1.5.5")
        create_column(person_report_statement, title2, "Ilmiy darajaga ega xodimlar", "Сотрудники с учёной степенью", "1.2.1.6")
        create_column(person_report_statement, title2, "Xorijiy til biladigan xodimlar", "Сотрудники, владеющие иностранным языком", "1.2.1.7")
        create_column(person_report_statement, title2, "Chet elda tahsil olgan va malaka oshirgan xodimlar", "Сотрудники, обучавшиеся за границей и повысившие квалификацию", "1.2.1.8")

        # === 3-Ilova ===
        ilova3 = create_column(person_report_statement, None, "3-ilova", "Приложение 3", "1.3")
        title3 = create_column(person_report_statement, ilova3,
                               "Tizim tashkilotlaridagi yangi ish o‘rinlari haqida ma’lumot",
                               "Информация о новых рабочих местах в системе",
                               "1.3.1")

        create_column(person_report_statement, title3, "Tashkilot nomi", "Название организации", "1.3.1.1", is_organization=True)
        create_column(person_report_statement, title3, "Jami yangi yaratilgan ish o'rinlar soni", "Общее количество новых рабочих мест", "1.3.1.2")

        shundan3 = create_column(person_report_statement, title3, "Shundan", "Из них", "1.3.1.3")
        create_column(person_report_statement, shundan3, "Doimiy", "Постоянные", "1.3.1.3.1")
        create_column(person_report_statement, shundan3, "Mavsumiy", "Сезонные", "1.3.1.3.2")

        yosh30 = create_column(person_report_statement, shundan3, "Yoshlar (30 yoshgacha)", "Молодёжь (до 30 лет)", "1.3.1.3.3")
        create_column(person_report_statement, yosh30, "Erkak", "Мужчины", "1.3.1.3.3.1")
        create_column(person_report_statement, yosh30, "Xotin qizlar", "Женщины", "1.3.1.3.3.2")

        create_column(person_report_statement, shundan3, "Temir daftar va ayollar daftariga kiritilgan", "Включённые в железную и женскую книги", "1.3.1.3.4")
        create_column(person_report_statement, shundan3, "Kambag’al axolidan olingan", "Из числа малообеспеченных", "1.3.1.3.5")
        create_column(person_report_statement, shundan3, "Kasanachilik asosida", "На основе надомного труда", "1.3.1.3.6")


        self.stdout.write(self.style.SUCCESS(f"Employee report created ! "))