from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    def handle(self, *args, **options):

        # ========== Boshoqli Don ilovasi ==========
        def create_column(statement, parent, title_uz, title_ru, ordering, is_organization=False, is_user_input=True):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=ordering,
                is_organization=is_organization,
                is_user_input=is_user_input
            )

        def create_triplet(statement, parent, base_ordering, is_user_input=True):
            sub_titles = [("ga", "га"), ("s/ga", "ц/га"), ("tn", "т")]
            for i, (title_uz, title_ru) in enumerate(sub_titles, start=1):
                create_column(
                    statement,
                    parent,
                    title_uz,
                    title_ru,
                    f"{base_ordering}.{i}",
                    is_user_input=is_user_input
                )

        def create_village(statement, parent, base_ordering, is_user_input=True):
            sub_titles = [
                ("Jami maydon, ga", "Общая площадь, га"),
                ("Shundan hosilga kirgani", "Из них получен урожай"),
                ("s/ga", "ц/га"),
                ("tn", "т")
            ]
            for i, (title_uz, title_ru) in enumerate(sub_titles, start=1):
                create_column(
                    statement,
                    parent,
                    title_uz,
                    title_ru,
                    f"{base_ordering}.{i}",
                    is_user_input=is_user_input
                )

        forest_add = Statement.objects.create(
            name_uz="O'rmonlardan qo'shimcha foydalanish",
            name_ru="Дополнительное использование лесов",
            period=PeriodChoices.YILLIK
        )
        statement_forest_add = Statement.objects.create(
            parent=forest_add,
            name_uz="Qishloq xo'jaligi",
            name_ru="Сельское хозяйство"
        )

        # ========== Boshoqli Don ilovasi ==========
        forest_app = create_column(
            statement_forest_add,
            None,
            "Boshoqli don ilovasi",
            "Приложение: Зерновые культуры",
            "1",
        )

        title_forest_app = create_column(
            statement_forest_add,
            forest_app,
            "Agentlik tizimidagi xo'jaliklarda 2025 yilda boshoqli don ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot",
            "Информация о посеве зерновых культур и производстве продукции в хозяйствах системы Агентства в 2025 году",
            "1.1"
        )

        create_column(
            statement_forest_add,
            title_forest_app,
            "Tashkilot nomi",
            "Наименование хозяйства",
            "1.1.1",
            is_organization=True
        )

        boshoqli_don = create_column(
            statement_forest_add,
            title_forest_app,
            "Boshoqli don",
            "Зерновые культуры",
            "1.1.2"
        )

        create_triplet(statement_forest_add, boshoqli_don, "1.1.2", is_user_input=False)

        create_column(
            statement_forest_add,
            title_forest_app,
            "Davlatga topshirilgan bug'doy (tonna)",
            "Пшеница, переданная государству (т)",
            "1.1.3"
        )

        shu_jumladan = create_column(
            statement_forest_add,
            title_forest_app,
            "Shu jumladan",
            "В том числе",
            "1.1.4"
        )

        crops = [
            ("Bug'doy", "Пшеница", "1.1.4.1"),
            ("Arpa", "Ячмень", "1.1.4.2"),
            ("Makkajo'xori don", "Кукурузное зерно", "1.1.4.3"),
            ("Tarix", "Просо", "1.1.4.4"),
            ("Sholi", "Рис", "1.1.4.5"),
            ("Paxta", "Хлопок", "1.1.4.6")
        ]

        for title_uz, title_ru, ordering in crops:
            crop = create_column(statement_forest_add, shu_jumladan, title_uz, title_ru, ordering)
            create_triplet(statement_forest_add, crop, ordering)

        # ======= Sabzavotlar ilovasi ========
        second_forest_app = create_column(
            statement_forest_add,
            None,
            "Sabzavot ilovasi",
            "Приложение: Овощные культуры",
            "2"
        )

        second_title_forest = create_column(
            statement_forest_add,
            second_forest_app,
            "Agentlik tizimidagi xo'jaliklarda 2025 yilda sabzavot ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot",
            "Информация о посеве овощных культур и производстве продукции в хозяйствах системы Агентства в 2025 году",
            "2.1"
        )

        create_column(
            statement_forest_add,
            second_title_forest,
            "Tashkilot nomi",
            "Наименование хозяйства",
            "2.1.1",
            is_organization=True
        )

        sabzavot = create_column(
            statement_forest_add,
            second_title_forest,
            "Sabzavot",
            "Овощи",
            "2.1.2",
            is_user_input=False
        )
        create_triplet(statement_forest_add, sabzavot, "2.1.2", is_user_input=False)

        wu_jumladan = create_column(
            statement_forest_add,
            second_title_forest,
            "Shu jumladan",
            "В том числе",
            "2.1.3"
        )

        vegetables = [
            ("Sarimsoq piyoz", "Чеснок", "2.1.3.1"),
            ("Piyoz", "Лук", "2.1.3.2"),
            ("Achchiq qalampir", "Острый перец", "2.1.3.3"),
            ("Bolgar qalampiri", "Сладкий перец", "2.1.3.4"),
            ("Kartoshka", "Картофель", "2.1.3.5"),
            ("Sabzi", "Морковь", "2.1.3.6"),
            ("Karam", "Капуста", "2.1.3.7"),
            ("Pomidor", "Помидор", "2.1.3.8"),
            ("Bodring", "Огурец", "2.1.3.9"),
            ("Qizil lavlagi", "Свёкла", "2.1.3.10"),
            ("Sholg'om", "Репа", "2.1.3.11"),
            ("Boshqa ekinlar", "Другие культуры", "2.1.3.12")
        ]

        for title_uz, title_ru, ordering in vegetables:
            veg = create_column(statement_forest_add, wu_jumladan, title_uz, title_ru, ordering)
            create_triplet(statement_forest_add, veg, ordering)

            # ========== Poliz ilovasi ==========
        third_forest_app = create_column(
            statement_forest_add,
            None,
            "Poliz ilovasi",
            "Приложение: Бахча маҳсулотлари",
            "3"
        )

        third_title_forest = create_column(
            statement_forest_add,
            third_forest_app,
            "Agentlik tizimidagi xo'jaliklarda 2025 yilda poliz ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot",
            "Информация о посеве бахчевых культур и производстве продукции в хозяйствах системы Агентства в 2025 году",
            "3.1"
        )

        create_column(
            statement_forest_add,
            third_title_forest,
            "Tashkilot nomi",
            "Наименование хозяйства",
            "3.1.1",
            is_organization=True
        )

        poliz = create_column(
            statement_forest_add,
            third_title_forest,
            "Poliz",
            "Бахча",
            "3.1.2",
            is_user_input=False
        )
        create_triplet(statement_forest_add, poliz, "3.1.2", is_user_input=False)

        jumladan_poliz = create_column(
            statement_forest_add,
            third_title_forest,
            "Shu jumladan",
            "В том числе",
            "3.1.3"
        )

        poliz_crops = [
            ("Tarvuz", "Арбуз", "3.1.3.1"),
            ("Qovun", "Дыня", "3.1.3.2"),
            ("Oshqovoq", "Тыква", "3.1.3.3")
        ]

        for title_uz, title_ru, ordering in poliz_crops:
            crop = create_column(statement_forest_add, jumladan_poliz, title_uz, title_ru, ordering)
            create_triplet(statement_forest_add, crop, ordering)

            # ========== Moyli ilovasi ==========
        fourth_forest_app = create_column(
            statement_forest_add,
            None,
            "Moyli ilovasi",
            "Приложение: Масличные культуры",
            "4"
        )

        fourth_title_forest = create_column(
            statement_forest_add,
            fourth_forest_app,
            "Agentlik tizimidagi xo'jaliklarda 2025 yilda moyli ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot",
            "Информация о посеве масличных культур и производстве продукции в хозяйствах системы Агентства в 2025 году",
            "4.1"
        )

        create_column(
            statement_forest_add,
            fourth_title_forest,
            "Tashkilot nomi",
            "Наименование хозяйства",
            "4.1.1",
            is_organization=True
        )

        moyli = create_column(
            statement_forest_add,
            fourth_title_forest,
            "Moyli ekinlar",
            "Масличные культуры",
            "4.1.2",
            is_user_input=False
        )
        create_triplet(statement_forest_add, moyli, "4.1.2", is_user_input=False)

        jumladan_moyli = create_column(
            statement_forest_add,
            fourth_title_forest,
            "Shu jumladan",
            "В том числе",
            "4.1.3"
        )

        moyli_crops = [
            ("Mashar", "Горчица", "4.1.3.1"),
            ("Kunjut", "Кунжут", "4.1.3.2"),
            ("Yer yong'oq", "Арахис", "4.1.3.3"),
            ("Kungaboqar", "Подсолнечник", "4.1.3.4"),
            ("Zig'ir", "Лён", "4.1.3.5")
        ]

        for title_uz, title_ru, ordering in moyli_crops:
            crop = create_column(statement_forest_add, jumladan_moyli, title_uz, title_ru, ordering)
            create_triplet(statement_forest_add, crop, ordering)

            # ========== Dukkakli ilovasi ==========
        fifth_forest_app = create_column(
            statement_forest_add,
            None,
            "Dukkakli ilovasi",
            "Приложение: Бобовые культуры",
            "5"
        )

        fifth_title_forest = create_column(
            statement_forest_add,
            fifth_forest_app,
            "Agentlik tizimidagi xo'jaliklarda 2025 yilda dukkakli ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot",
            "Информация о посеве бобовых культур и производстве продукции в хозяйствах системы Агентства в 2025 году",
            "5.1"
        )

        create_column(
            statement_forest_add,
            fifth_title_forest,
            "Tashkilot nomi",
            "Наименование хозяйства",
            "5.1.1",
            is_organization=True
        )

        dukkakli = create_column(
            statement_forest_add,
            fifth_title_forest,
            "Dukkakli ekinlar",
            "Бобовые культуры",
            "5.1.2",
            is_user_input=False
        )
        create_triplet(statement_forest_add, dukkakli, "5.1.2", is_user_input=False)

        jumladan_dukkakli = create_column(
            statement_forest_add,
            fifth_title_forest,
            "Shu jumladan",
            "В том числе",
            "5.1.3"
        )

        dukkakli_crops = [
            ("No'xat", "Нут", "5.1.3.1"),
            ("Mosh", "Маш", "5.1.3.2"),
            ("Loviya", "Фасоль", "5.1.3.3"),
            ("Qizil loviya", "Красная фасоль", "5.1.3.4")
        ]

        for title_uz, title_ru, ordering in dukkakli_crops:
            crop = create_column(statement_forest_add, jumladan_dukkakli, title_uz, title_ru, ordering)
            create_triplet(statement_forest_add, crop, ordering)

        # ========== Ozuqa ilovasi ==========
        sixth_forest_app = create_column(
            statement_forest_add,
            None,
            "Ozuqa ilovasi",
            "Кормовые культуры",
            "6"
        )

        sixth_title_forest = create_column(
            statement_forest_add,
            sixth_forest_app,
            "Agentlik tizimidagi xo'jaliklarda 2025 yilda ozuqa ekinlarini ekish va mahsulot yetishtirish to'g'risida ma'lumot",
            "Информация о посеве кормовых культур и производстве продукции в хозяйствах системы Агентства в 2025 году",
            "6.1"
        )

        create_column(
            statement_forest_add,
            sixth_title_forest,
            "Tashkilot nomi",
            "Наименование хозяйства",
            "6.1.1",
            is_organization=True
        )

        ozuqa = create_column(
            statement_forest_add,
            sixth_title_forest,
            "Ozuqa ekinlari",
            "Кормовые культуры",
            "6.1.2",
            is_user_input=False
        )
        create_triplet(statement_forest_add, ozuqa, "6.1.2", is_user_input=False)

        jumladan_ozuqa = create_column(
            statement_forest_add,
            sixth_title_forest,
            "Shu jumladan",
            "В том числе",
            "6.1.3"
        )

        ozuqa_crops = [
            ("Makkajo'xori (silos)", "Кукуруза (силос)", "6.1.3.1"),
            ("Beda", "Люцерна", "6.1.3.2"),
            ("Somon", "Солома", "6.1.3.3"),
            ("Dag'al ozuqa", "Грубые корма", "6.1.3.4")
        ]

        for title_uz, title_ru, ordering in ozuqa_crops:
            crop = create_column(statement_forest_add, jumladan_ozuqa, title_uz, title_ru, ordering)
            create_triplet(statement_forest_add, crop, ordering)

        suprug = create_column(
            statement_forest_add,
            sixth_title_forest,
            "Supurgi",
            "Сенаж",
            "6.1.4"
        )

        suprug_children = [
            ("t/ko'", "т/куб", "6.1.4.1"),
            ("m/ko'", "м/куб", "6.1.4.2"),
            ("s/ko'm", "с/куб.м", "6.1.4.3")
        ]

        for title_uz, title_ru, ordering in suprug_children:
            create_column(statement_forest_add, suprug, title_uz, title_ru, ordering)

            # ========== Bog'-Tok ilovasi ==========
        seventh_forest_app = create_column(
            statement_forest_add,
            None,
            "Bog'-Tok ilovasi",
            "Приложение: Сады и виноградники",
            "7"
        )

        seventh_title_forest = create_column(
            statement_forest_add,
            seventh_forest_app,
            "Agentlik tizimidagi xo'jaliklarda 2025 yilda mevali bog'lar va tokzorlar ekish va hosil yetishtirish to'g'risida ma'lumot",
            "Информация о посеве и урожайности садов и виноградников в хозяйствах системы Агентства в 2025 году",
            "7.1"
        )

        create_column(
            statement_forest_add,
            seventh_title_forest,
            "Tashkilot nomi",
            "Наименование хозяйства",
            "7.1.1",
            is_organization=True
        )

        jami_bog_tok = create_column(
            statement_forest_add,
            seventh_title_forest,
            "Jami bog' va tokzorlar",
            "Общие сады и виноградники",
            "7.1.2",
            is_user_input=False
        )
        create_village(statement_forest_add, jami_bog_tok, "7.1.2", is_user_input=False)

        shu_jumladan_bogtok = create_column(
            statement_forest_add,
            seventh_title_forest,
            "Shu jumladan",
            "В том числе",
            "7.1.3"
        )

        urugli = create_column(
            statement_forest_add,
            shu_jumladan_bogtok,
            "Urug'li",
            "Семечковые",
            "7.1.3.1"
        )
        create_village(statement_forest_add, urugli, "7.1.3.1")

        danakli = create_column(
            statement_forest_add,
            shu_jumladan_bogtok,
            "Danakli",
            "Косточковые",
            "7.1.3.2"
        )
        create_village(statement_forest_add, danakli, "7.1.3.2")

        uzumzor = create_column(
            statement_forest_add,
            shu_jumladan_bogtok,
            "Uzumzor",
            "Виноградник",
            "7.1.3.3"
        )
        create_village(statement_forest_add, uzumzor, "7.1.3.3")

        create_column(statement_forest_add, seventh_title_forest, "2017-2024 yildan qo'shilgan bog'lar",
                      "Сады, добавленные с 2017 по 2024 год", "7.1.4")

        # ========== Bodom va Pista ilovasi ==========
        eighth_forest_app = create_column(
            statement_forest_add,
            None,
            "Bodom va Pista ilovasi",
            "Приложение: Миндаль и фисташка",
            "8"
        )

        eighth_title_forest = create_column(
            statement_forest_add,
            eighth_forest_app,
            "Agentlik tizimidagi xo'jaliklarda 2025 yilda yong'oqmevali mahsulotlar yetishtirish to'g'risida ma'lumot",
            "Информация о производстве орехоплодных культур в хозяйствах системы Агентства в 2025 году",
            "8.1"
        )

        create_column(
            statement_forest_add,
            eighth_title_forest,
            "Tashkilot nomi",
            "Наименование лесных хозяйств",
            "8.1.1",
            is_organization=True
        )

        jami_yongoq = create_column(
            statement_forest_add,
            eighth_title_forest,
            "Jami yong'oqmevalilar",
            "Общие орехоплодные культуры",
            "8.1.2",
            is_user_input=False
        )
        create_village(statement_forest_add, jami_yongoq, "8.1.2", is_user_input=False)

        shu_jumladan_2 = create_column(
            statement_forest_add,
            eighth_title_forest,
            "Shu jumladan",
            "В том числе",
            "8.1.3"
        )

        grek = create_column(
            statement_forest_add,
            shu_jumladan_2,
            "Grek yong'og'i",
            "Грецкий орех",
            "8.1.3.1"
        )
        create_village(statement_forest_add, grek, "8.1.3.1")

        bodom = create_column(
            statement_forest_add,
            shu_jumladan_2,
            "Bodom",
            "Миндаль",
            "8.1.3.2"
        )
        create_village(statement_forest_add, bodom, "8.1.3.2")

        pista = create_column(
            statement_forest_add,
            shu_jumladan_2,
            "Pista",
            "Фисташка",
            "8.1.3.3"
        )
        create_village(statement_forest_add, pista, "8.1.3.3")

        tabiiy = create_column(
            statement_forest_add,
            eighth_title_forest,
            "Tabiiy mevalarni tayyorlash, tn",
            "Подготовка природных фруктов, тн",
            "8.1.4"
        )
        StatementColumn.objects.create(
            statement=statement_forest_add,
            parent=tabiiy,
            title_uz="Ho‘l meva",
            title_ru="Свежий фрукт",
            ordering="8.1.4.1"
        )
        StatementColumn.objects.create(
            statement=statement_forest_add,
            parent=tabiiy,
            title_uz="Grek yong‘og‘i",
            title_ru="Грецкий орех",
            ordering="8.1.4.2"
        )
        StatementColumn.objects.create(
            statement=statement_forest_add,
            parent=tabiiy,
            title_uz="Pista",
            title_ru="Фисташки",
            ordering="8.1.4.3"
        )

        self.stdout.write(
            self.style.SUCCESS("✅ Uspeshno yaratildi 'Sel’skoe khozyaystvo' Statement and Columns.")
        )
