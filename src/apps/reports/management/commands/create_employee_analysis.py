from django.core.management import BaseCommand
from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices

class Command(BaseCommand):
    help = "Create Statement Columns for 'Xodimlar hisobi taxlili'"

    def handle(self, *args, **options):
        person_statement = Statement.objects.filter(name="Insoniyat resurslarini boshqarish").first()

        person_report_statement = Statement.objects.create(
            parent=person_statement,
            name_uz="Xodimlar hisobi taxlili",
            name_ru="Анализ учета кадров",
            period=PeriodChoices.YILLIK
        )

        def create_column(statement, parent, uz, ru, ordering, is_org=False,is_user_input=True):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title=uz,
                title_uz=uz,
                title_ru=ru,
                ordering=ordering,
                is_organization=is_org
            )

        # --- 4-ilova: Xodimlar statistikasi ---
        ilova_4 = create_column(
            person_report_statement,
            None,
            "4-ilova",
            "Приложение 4",
            "1"
        )

        stats_root = create_column(
            person_report_statement,
            ilova_4,
            "2025 yil uchun xodimlar statistikasi to‘g‘risidagi ma’lumot",
            "Информация о статистике сотрудников за 2025 год",
            "1.1"
        )

        # Statik ustunlar
        static_columns = [
            ("Tashkilot nomi", "Наименование организации", "1.1.1", True),
            ("Tasdiqlangan shtat birligi bo‘yicha xodimlar soni (faqat boshqaruv xodimlari)",
             "Количество сотрудников по утвержденной штатной единице (только управленческий состав)", "1.1.2", False),
            ("Amaldagi xodimlar soni (faqat boshqaruv xodimlari)",
             "Фактическое количество сотрудников (только управленческий состав)", "1.1.3", False),
        ]
        for uz, ru, order, is_org in static_columns:
            create_column(person_report_statement, stats_root, uz, ru, order, is_org)

        # Yosh bo‘yicha tarkib
        age_column = create_column(
            person_report_statement,
            stats_root,
            "Xodimlarning yosh bo‘yicha tarkibi",
            "Возрастной состав сотрудников",
            "1.1.4"
        )

        age_fields = [
            ("30 yoshgacha bo‘lgan", "До 30 лет"),
            ("30 yoshdan 40 yoshgacha bo‘lgan", "От 30 до 40 лет"),
            ("10 yoshdan 50 yoshgacha bo‘lgan", "От 40 до 50 лет"),
            ("50 yoshdan 60 yoshgacha bo‘lgan", "От 50 до 60 лет"),
            ("60 yoshdan yuqori bo‘lgan", "Старше 60 лет"),
            ("Yoshga doir pensiya olayotgan va pensiyaga chiqish huquqiga ega bo‘lib ishlayotgan",
             "Получающие пенсию по возрасту и имеющие право на выход на пенсию"),
            ("2025 yilda pensiya yoshiga yetadigan", "Достигающие пенсионного возраста в 2025 году"),
        ]

        for i, (uz, ru) in enumerate(age_fields, 1):
            create_column(
                person_report_statement,
                age_column,
                f"{uz} boshqaruv xodimlari soni",
                f"Количество руководящих сотрудников {ru}",
                f"1.1.4.{i}"
            )

        # Ish staji bo‘yicha tarkib
        exp_column = create_column(
            person_report_statement,
            stats_root,
            "Xodimlarning ish staji bo‘yicha tarkibi",
            "Состав сотрудников по трудовому стажу",
            "1.1.5"
        )

        stajlar = [
            ("2 yilgacha", "До 2 лет"),
            ("2 yildan ortiq", "Свыше 2 лет"),
        ]

        for i, (uz, ru) in enumerate(stajlar, 1):
            create_column(person_report_statement, exp_column, uz, ru, f"1.1.5.{i}")

        # Ma’lumoti bo‘yicha tarkib
        info_column = create_column(
            person_report_statement,
            stats_root,
            "Xodimlarning ma’lumoti bo‘yicha tarkibi",
            "Состав сотрудников по образованию",
            "1.1.6"
        )

        info_fields = [
            ("Pedagogika fanlari", "Педагогические науки"),
            ("Gumanitar fanlar", "Гуманитарные науки"),
            ("Tabiiy fanlar, matematika va fizika", "Естественные науки, математика и физика"),
            ("Sanoat sohasi", "Промышленная сфера"),
            ("Jurnalistika va axborot", "Журналистика и информация"),
            ("Iqtisod, biznes va boshqaruv", "Экономика, бизнес и управление"),
            ("Huquq va siyosat", "Право и политика"),
            ("Muhandislik ishi", "Инженерное дело"),
            ("Ishlab chiqarish va ishlov berish sohalari", "Производственные и перерабатывающие отрасли"),
            ("Arxitektura va qurilish", "Архитектура и строительство"),
            ("Qishloq, o‘rmon va baliq xo‘jaligi, irrigatsiya va veterinariya",
             "Сельское, лесное и рыбное хозяйство, ирригация и ветеринария"),
            ("Xizmat ko‘rsatish sohasi", "Сфера обслуживания"),
            ("Transport va logistika", "Транспорт и логистика"),
            ("Ijtimoiy va xulq-atvorga mansub fanlar", "Социальные и поведенческие науки"),
            ("Sog‘liqni saqlash", "Здравоохранение"),
            ("Kompyuter texnologiyalari va informatika", "Компьютерные технологии и информатика"),
        ]

        for i, (uz, ru) in enumerate(info_fields, 1):
            create_column(person_report_statement, info_column, uz, ru, f"1.1.6.{i}")

        # Ilmiy daraja
        degree_column = create_column(
            person_report_statement,
            stats_root,
            "Xodimlarning darajasi bo‘yicha tarkibi",
            "Состав сотрудников по научным степеням",
            "1.1.7"
        )

        degree_fields = [
            ("PHD, fan nomzodi ilmiy darajasiga ega xodimlar soni",
             "Количество сотрудников с ученой степенью PhD, кандидата наук"),
            ("Magistr darajasiga ega xodimlar soni", "Количество сотрудников со степенью магистра"),
            ("Bakalavr darajasiga ega xodimlar soni", "Количество сотрудников со степенью бакалавра"),
            ("O‘rta maxsus ma’lumotli xodimlar soni", "Количество сотрудников со средним специальным образованием"),
            ("Xalqaro e’tirof etilgan diplomga ega xodimlar soni",
             "Количество сотрудников с международно признанным дипломом"),
        ]

        for i, (uz, ru) in enumerate(degree_fields, 1):
            create_column(person_report_statement, degree_column, uz, ru, f"1.1.7.{i}")

        # Sertifikatlar
        # Xorijiy tillarni biluvchi xodimlar
        lang_column = create_column(
            person_report_statement,
            stats_root,
            "Xorijiy tillarni biluvchi xodimlar",
            "Сотрудники, владеющие иностранными языками",
            "1.1.8"
        )

        sertifikatlar = [
            ("Xalqaro sertifikatga ega xodimlar soni", "Количество сотрудников с международным сертификатом"),
            ("Milliy sertifikatga ega xodimlar soni", "Количество сотрудников с национальным сертификатом"),
        ]

        for i, (uz, ru) in enumerate(sertifikatlar, 1):
            create_column(
                person_report_statement,
                lang_column,
                uz,
                ru,
                f"1.1.8.{i}"
            )

        # Vakant lavozimlar bo‘yicha mutaxassisliklar — 1.4.1.9
        vak_column = create_column(
            person_report_statement,
            stats_root,
            "Vakant lavozimlar bo‘yicha mutaxassisliklar",
            "Специальности по вакантным должностям",
            "1.1.9"
        )

        vak_fields = [
            ("Pedagogika fanlari", "Педагогические науки"),
            ("Gumanitar fanlar", "Гуманитарные науки"),
            ("Tabiiy fanlar, matematika va fizika", "Естественные науки, математика и физика"),
            ("San’at sohasi", "Сфера искусства"),
            ("Jurnalistika va axborot", "Журналистика и информация"),
            ("Iqtisod, biznes va boshqaruv", "Экономика, бизнес и управление"),
            ("Huquq va siyosat", "Право и политика"),
            ("Muhandislik ishi", "Инженерное дело"),
            ("Ishlab chiqarish va ishlov berish sohalari", "Производственные и перерабатывающие отрасли"),
            ("Arxitektura va qurilish", "Архитектура и строительство"),
            ("Qishloq, o‘rmon va baliq xo‘jaligi, irrigatsiya va veterinariya",
             "Сельское, лесное и рыбное хозяйство, ирригация и ветеринария"),
            ("Xizmat ko‘rsatish sohasi", "Сфера обслуживания"),
            ("Transport va logistika", "Транспорт и логистика"),
            ("Ijtimoiy va xulq-atvorga mansub fanlar", "Социальные и поведенческие науки"),
            ("Sog‘liqni saqlash", "Здравоохранение"),
            ("Kompyuter texnologiyalari va informatika", "Компьютерные технологии и информатика"),
        ]

        for i, (uz, ru) in enumerate(vak_fields, 1):
            create_column(person_report_statement, vak_column, uz, ru, f"1.1.9.{i}")

        # Utility functions

        def create_col(parent, uz, ru, ord, is_org=False,is_user_input=True):
            return StatementColumn.objects.create(
                statement=person_report_statement,
                parent=parent,
                title=uz,
                title_uz=uz,
                title_ru=ru,
                ordering=ord,
                is_organization=is_org,
                is_user_input=is_user_input,
            )

        # 5-ilova: O‘rmon xo‘jaligi xodimlari
        ilova_5 = create_col(None, "5-ilova", "Приложение 5", "2")
        title_5 = create_col(ilova_5,
                             "O‘rmon xo‘jaligi xodimlari to‘g‘risidagi statistik tahlili",
                             "Статистический анализ сотрудников лесного хозяйства",
                             "2.1")

        # F1: Mehnat va muhofaza
        create_col(title_5, "Tashkilot nomi", "Наименование организации", "2.1.1", is_org=True)
        f1 = create_col(title_5,
                        "Xodimlarning ish faoliyati me'yorlari va mehnat muhofazasi",
                        "Нормы труда и охрана труда сотрудников",
                        "2.1.2")

        create_col(f1, "Tasdiqlangan shtat birligi bo‘yicha xodimlar soni",
                   "Численность сотрудников по штатному расписанию", "2.1.2.1")
        create_col(f1, "Shundan xotin-qizlar soni", "В том числе женщины", "2.1.2.2")

        f1_1 = create_col(f1, "Xodimlarning yosh bo‘yicha tarkibi", "Возрастной состав сотрудников", "2.1.2.3")
        ages = [
            ("30 yoshgacha bo‘lgan xodimlar soni", "Количество сотрудников до 30 лет"),
            ("30 yoshdan 50 yoshgacha bo‘lgan xodimlar soni", "Сотрудников от 30 до 50 лет"),
            ("20 yoshdan yuqori bo‘lgan xodimlar soni", "Сотрудников старше 50 лет"),
        ]
        for idx, (uz, ru) in enumerate(ages, 1):
            create_col(f1_1, uz, ru, f"2.1.2.3.{idx}")

        f1_2 = create_col(f1, "Xodim ish vaqti me'yorlarining ish hajmiga mutanosibligi (foizda)",
                          "Соответствие рабочего времени норме труда (в %)", "2.1.2.4")
        create_col(f1_2, "Yillik rejaga muvofiq amalga oshiriladigan ish",
                   "Работы, выполненные согласно годовому плану", "2.1.2.4.1")
        create_col(f1_2, "Va shunga muvofiq ish hajmining mavjudligi",
                   "Наличие объёма выполненных работ", "2.1.2.4.2")

        create_col(f1, "Bir hisobot yili davomida mehnat ta’tiliga chiqqan xodimlar soni",
                   "Количество сотрудников, использовавших трудовой отпуск за отчетный год", "2.1.2.5")
        f1_4 = create_col(f1, "Xodimning ish vaqtidan tashqari ishlaganligi uchun qo‘shimcha to‘lov to‘langanligi",
                          "Оплата за переработки сотрудников", "2.1.2.6")
        create_col(f1_4, "Mablag‘ sarfi, mln. so‘mda", "Сумма расходов (млн. сум)", "2.1.2.6.1")
        create_col(f1_4, "Dam olish va bayram kunlari ishga jalb qilingan xodimlar soni",
                   "Количество сотрудников, привлекавшихся в выходные и праздничные дни", "2.1.2.6.2")

        create_col(f1,
                   "Xodimlarning ish vaqtini hisobga olishning avtomatlashtirilgan tizimining mavjudligi (mavjud yoki mavjud emas)",
                   "Наличие автоматизированной системы учёта рабочего времени", "2.1.2.7")

        # F2: Kadrlar oqimi
        f2 = create_col(title_5, "Kadrlar qo‘nimsizligi va xodimlarning kasbiy o‘sishi",
                        "Движение кадров и профессиональный рост", "2.1.3")
        f2_1 = create_col(f2, "Xodimlarning bir lavozimda bo‘lishi davomiyligi (yillarda)",
                          "Продолжительность пребывания сотрудников на должностях (лет)", "2.1.3.1")
        for idx, pos in enumerate(
                ["Direktor", "Direktor o‘rinbosari", "Bo‘lim boshlig‘i", "Sho‘ba mudiri", "Bosh mutaxassislar",
                 "Mutaxassislar"], 1):
            create_col(f2_1, pos, pos, f"2.1.3.1.{idx}")

        f2_2 = create_col(f2, "Xodimlarni ishga qabul qilish", "Приём на работу сотрудников", "2.1.3.2")
        for idx, y in enumerate(["2025‑yil", "2024‑yil", "2023‑yil", "2022‑yil"], 1):
            create_col(f2_2, y, y, f"2.1.3.2.{idx}")

        f2_3 = create_col(f2, "Xodimlarni ishdan bo‘shatish", "Увольнение сотрудников", "2.1.3.3")
        for idx, y in enumerate(["2025‑yil", "2024‑yil", "2023‑yil", "2022‑yil"], 1):
            create_col(f2_3, y, y, f"2.1.3.3.{idx}")

        f2_4 = create_col(f2, "Xodimlarning kasbiy o‘sishi", "Профессиональный рост сотрудников", "2.1.3.4")
        for idx, (uz, ru) in enumerate([
            ("Yuqori lavozimlar", "Высшие должности"),
            ("Teng lavozimlar", "Равные должности"),
            ("Quyi lavozimlar", "Низшие должности")
        ], 1):
            create_col(f2_4, uz, ru, f"2.1.3.4.{idx}")

        f2_4_1 = create_col(f2_4, "Xodimlarning kasbiy o‘sishi (to‘liq)",
                            "Профессиональный рост сотрудников (детально)", "2.1.3.4.4")
        for idx, pos in enumerate(
                ["Departament mudiri", "Boshqarma boshlig‘i", "Bo‘lim boshlig‘i", "Sho‘ba mudiri", "Mutaxassislar‑2"],
                1):
            create_col(f2_4_1, pos, pos, f"2.1.3.4.4.{idx}")

        f2_5 = create_col(f2, "Malaka oshirgan va qayta o‘qish kurslariga qatnashgan xodimlar soni",
                          "Количество сотрудников, прошедших повышение квалификации и переподготовку", "2.1.3.5")
        create_col(f2_5, "Jami", "Всего", "2.1.3.5.1",is_user_input=False)
        f2_5_1 = create_col(f2_5, "shu jumladan", "в том числе", "2.1.3.5.2")
        for idx, pos in enumerate(
                ["Departament mudiri", "Boshqarma boshlig‘i", "Bo‘lim boshlig‘i", "Sho‘ba mudiri", "Mutaxassislar‑2"],
                1):
            create_col(f2_5_1, pos, pos, f"2.1.3.5.2.{idx}")

        # 1-2: Oddiy (childsiz) ustunlar
        tail_items = [
            ("Kasallik varaqasi ... (soni va o‘rtacha)",
             "Больничные листы ... (количество и средняя продолжительность)", "2.1.3.6"),
            ("Xodimlarni davolash va tibbiy profilaktika choralari uchun to‘langan mablag‘",
             "Расходы на лечение и профилактику сотрудников", "2.1.3.7"),
        ]
        for uz, ru, ord in tail_items:
            create_col(f2, uz, ru, ord)

        # 3: Xodimlarning kasallik turlari (childlari bor)
        f2_8 = create_col(
            f2,
            "Xodimlarning kasallik turlari (5 yillik dinamikasi bilan)",
            "Типы заболеваний сотрудников (с 5-летней динамикой)",
            "2.1.3.8"
        )
        create_col(f2_8, "Jami", "Всего", "2.1.3.8.1",is_user_input=False)
        f2_8_1 = create_col(f2_8, "shu jumladan", "в том числе", "2.1.3.8.2")
        for idx, (uz, ru) in enumerate([
            ("Yurak va qon tomir kasalliklari", "Заболевания сердца и сосудов"),
            ("Asab kasalliklari", "Нервные заболевания"),
            ("Oshqozon-ichak kasalliklari", "Желудочно-кишечные заболевания"),
        ], 1):
            create_col(f2_8_1, uz, ru, f"2.1.3.8.2.{idx}")

        # 4: Sport bilan shug‘ullanuvchi xodimlar (childsiz, lekin o‘rtada)
        create_col(
            f2,
            "Sport bilan shug‘ullanuvchi xodimlar soni va to‘lovlar",
            "Число сотрудников, занимающихся спортом и выплаты",
            "2.1.3.9"
        )

        # 5: Madaniy-ma’rifiy tadbirlar (childlari bor)
        f2_10 = create_col(
            f2,
            "Madaniy-ma’rifiy tadbirlarda qatnashgan xodimlar va mablag‘lar",
            "Участие сотрудников в культурно-просветительских мероприятиях и расходы",
            "2.1.3.10"
        )
        create_col(f2_10, "Jami", "Всего", "2.1.3.10.1",is_user_input=False)
        f2_10_1 = create_col(f2_10, "shu jumladan", "в том числе", "2.1.3.10.2")
        for idx, (uz, ru) in enumerate([
            ("Teatr", "Театр"),
            ("Kino", "Кино"),
            ("Konsert", "Концерт"),
            ("Boshqalar", "Другие"),
        ], 1):
            create_col(f2_10_1, uz, ru, f"2.1.3.10.2.{idx}")

        # create_col funksiyasi (pastda qoladi)
        def create_col(parent, uz, ru, ord, is_org=False,is_user_input=True):
            return StatementColumn.objects.create(
                statement=person_report_statement,
                parent=parent,
                title=uz,
                title_uz=uz,
                title_ru=ru,
                ordering=ord,
                is_organization=is_org,
                is_user_input=is_user_input
            )

        # === 3-ILOVA / 6-ILOVA ===
        ilova_3 = create_col(
            None,
            "6-ilova",
            "Приложение 6",
            "3"
        )
        title_3 = create_col(
            ilova_3,
            "Oliy ta’lim muassasalari va kasb-hunar kollejlarini tamomlagan o‘rmon xo‘jaligi mutaxassislariga bo‘lgan talab",
            "Потребность в специалистах лесного хозяйства, окончивших вузы и колледжи",
            "3.1"
        )
        create_col(title_3, "Tashkilot nomi", "Наименование организации", "3.1.1", is_org=True)

        # 1-qism
        r1 = create_col(title_3,
                        "Bosh o‘rmonchi, o‘rmon xo‘jaligi muhandisi, o‘rmonchi, nazoratchi, egermayor va boshqa o‘rmon xo‘jaligi mutaxassislari",
                        "Главный лесничий, инженер, лесничий, инспектор, егермейстер и др. специалисты",
                        "3.1.2"
                        )
        create_col(r1, "Jami", "Всего", "3.1.2.1",is_user_input=False)
        r1_1 = create_col(r1, "Shundan", "В том числе", "3.1.2.2")

        # Oliy
        r1_1_1 = create_col(r1_1, "Oliy ma'lumotli", "С высшим образованием", "3.1.2.2.1")
        create_col(r1_1_1, "Jami", "Всего", "3.1.2.2.1.1")
        create_col(r1_1_1, "O'rmonshunos", "Лесовод", "3.1.2.2.1.2")

        # O'rta maxsus
        r1_1_2 = create_col(r1_1, "O'rta-maxsus malumotli", "Со средне-специальным образованием", "3.1.2.2.2")
        create_col(r1_1_2, "Jami", "Всего", "3.1.2.2.2.1")
        create_col(r1_1_2, "O'rmonshunos", "Лесовод", "3.1.2.2.2.2")

        # O'rta
        create_col(r1_1, "O'rta malumotli", "Со средним образованием", "3.1.2.2.3")

        # 2-qism: Mutaxassislarga bo‘lgan talab
        r2 = create_col(title_3,
                        "Ma’lumot darajasi bo‘yicha mutaxassislarga bo‘lgan talab",
                        "Потребность в специалистах по уровню образования",
                        "3.1.6"
                        )
        create_col(r2, "Jami", "Всего", "3.1.6.1",is_user_input=False)
        r2_1 = create_col(r2, "Shundan", "В том числе", "3.1.6.2")

        # Magister
        r2_1_1 = create_col(r2_1, "Magister", "Магистр", "3.1.6.2.1")
        for i, y in enumerate(["2025", "2026", "2027"], start=1):
            create_col(r2_1_1, y, y, f"3.1.6.2.1.{i}")

        # Oliy
        r2_1_2 = create_col(r2_1, "Oliy ma'lumotli", "С высшим образованием", "3.1.6.2.2")
        for i, y in enumerate(["2025", "2026", "2027"], start=1):
            create_col(r2_1_2, y, y, f"3.1.6.2.2.{i}")

        # O'rta maxsus
        r2_1_3 = create_col(r2_1, "O'rta-maxsus malumotli", "Со средне-специальным образованием", "3.1.6.2.3")
        for i, y in enumerate(["2025", "2026", "2027"], start=1):
            create_col(r2_1_3, y, y, f"3.1.6.2.3.{i}")

        self.stdout.write(self.style.SUCCESS(f"Employee created ! "))