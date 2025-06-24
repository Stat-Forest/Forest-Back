from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    def handle(self, *args, **options):

        # ========== Boshoqli Don ilovasi ==========
        def create_column(statement, parent, title, ordering, is_organization=False):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title=title,
                ordering=ordering,
                is_organization=is_organization
            )

        def create_triplet(statement, parent, base_ordering):
            sub_titles = ["га", "ц/га", "тн"]
            for i, title in enumerate(sub_titles, start=1):
                create_column(statement, parent, title, f"{base_ordering}.{i}")

        def create_village(statement, parent, base_ordering):
            sub_titles = ["Жами майдон, га", "Шундан ҳосилга киргани", "ц/га", "тн"]
            for i, title in enumerate(sub_titles, start=1):
                create_column(statement, parent, title, f"{base_ordering}.{i}")

        forest_add = Statement.objects.create(parent=None, name="O`rmonlardan qo`shimcha foydalanish")
        statement_forest_add = Statement.objects.create(parent=forest_add, name="Qishloq xo`jaligi")

        forest_app = create_column(statement_forest_add, None, "Boshokli don-ilovasi", "1")

        title_forest_app = create_column(
            statement_forest_add,
            forest_app,
            "Агентлик тизимидаги хўжаликларда 2025 йилда бошоқли дон экинларини экиш ва махсулотларини етиштириш тўғрисида Маълумот",
            "1.1"
        )

        create_column(statement_forest_add, title_forest_app, "Хўжалик номи", "1.1.1", is_organization=True)
        boshoqli_don = create_column(statement_forest_add, title_forest_app, "Бошоқли дон", "1.1.2")
        create_triplet(statement_forest_add, boshoqli_don, "1.1.2")
        create_column(statement_forest_add, title_forest_app, "Давлатга топширилган буғдой тонна", "1.1.3")

        shu_jumladan = create_column(statement_forest_add, title_forest_app, "Шу жумладан", "1.1.4")

        crops = [
            ("Буғдой", "1.1.4.1"),
            ("Арпа", "1.1.4.2"),
            ("Маккажўхори дон", "1.1.4.3"),
            ("Тарих", "1.1.4.4"),
            ("Шоли", "1.1.4.5"),
            ("Пахта", "1.1.4.6"),
        ]

        for title, ordering in crops:
            crop = create_column(statement_forest_add, shu_jumladan, title, ordering)
            create_triplet(statement_forest_add, crop, ordering)

        # ========== Sabzavot ilovasi ==========
        second_forest_app = create_column(statement_forest_add, None, "Сабзовот-ilovasi", "1")

        second_title_forest = create_column(
            statement_forest_add,
            second_forest_app,
            "Агентлик тизимидаги хўжаликларда 2025 йилда Сабзавот экинларини экилиши ва махсулотларни етиштириш тўғрисида Маълумот",
            "1.1"
        )

        create_column(statement_forest_add, second_title_forest, "Хўжалик номи", "1.1.1", is_organization=True)

        sabzavot = create_column(statement_forest_add, second_title_forest, "Сабзовот", "1.1.2")
        create_triplet(statement_forest_add, sabzavot, "1.1.2")

        wu_jumladan = create_column(statement_forest_add, second_title_forest, "Шу жумладан", "1.1.3")

        vegetables = [
            ("Саримсоқ пиёз", "1.1.3.1"),
            ("Пиёз", "1.1.3.2"),
            ("Аччиқ қалампир", "1.1.3.3"),
            ("Балғор", "1.1.3.4"),
            ("Картошка", "1.1.3.5"),
            ("Сабзи", "1.1.3.6"),
            ("Карам", "1.1.3.7"),
            ("Помидор", "1.1.3.8"),
            ("Бодиринг", "1.1.3.9"),
            ("Қизил лавлаги", "1.1.3.10"),
            ("Шолғом", "1.1.3.11"),
            ("Бошқа экинлар", "1.1.3.12"),
        ]

        for title, ordering in vegetables:
            veg = create_column(statement_forest_add, wu_jumladan, title, ordering)
            create_triplet(statement_forest_add, veg, ordering)

        # ========== Poliz ilovasi==========

        third_forest_app = create_column(statement_forest_add, None, "Полиз-ilovasi", "1")

        third_title_forest = create_column(
            statement_forest_add,
            third_forest_app,
            "Агентлик тизимидаги хўжаликларда 2025 йилда Полиз экинларини экилиши ва махсулотларини етиштириш тўғрисида Маълумот",
            "1.1"
        )

        create_column(statement_forest_add, third_title_forest, "Хўжалик номи", "1.1.1", is_organization=True)

        poliz = create_column(statement_forest_add, third_title_forest, "Полиз", "1.1.2")
        create_triplet(statement_forest_add, poliz, "1.1.2")

        jumladan = create_column(statement_forest_add, third_title_forest, "Шу жумладан", "1.1.3")

        poliz_crops = [
            ("Тарвуз", "1.1.3.1"),
            ("Қовун", "1.1.3.2"),
            ("Ошқовоқ", "1.1.3.3"),
        ]

        for title, ordering in poliz_crops:
            crop = create_column(statement_forest_add, jumladan, title, ordering)
            create_triplet(statement_forest_add, crop, ordering)

        # ========== Moyli ilovasi==========

        fourth_forest_app = create_column(statement_forest_add, None, "Мойли-ilovasi", "1")

        fourth_title_forest = create_column(
            statement_forest_add,
            fourth_forest_app,
            "Агентлик тизимидаги хўжаликларда 2025 йилда Мойли экинларини экилиши ва махсулотларини етиштириш"
            " тўғрисида Маълумот",
            "1.1"
        )

        create_column(statement_forest_add, fourth_title_forest, "Хўжалик номи", "1.1.1", is_organization=True)

        moyli_ekinlar = create_column(statement_forest_add, fourth_title_forest, "Мойли экинлар", "1.1.2")

        create_triplet(statement_forest_add, moyli_ekinlar, "1.1.2")

        uw_jumladan = create_column(statement_forest_add, fourth_title_forest, "Шу жумладан", "1.1.3")

        moyli_crops = [
            ("Масхар", "1.1.3.1"),
            ("Кунжут", "1.1.3.2"),
            ("Ер ёнғоқ", "1.1.3.3"),
            ("Кунгабоқар", "1.1.3.4"),
            ("Зиғир", "1.1.3.5"),
        ]

        for title, ordering in moyli_crops:
            crop = create_column(statement_forest_add, uw_jumladan, title, ordering)
            create_triplet(statement_forest_add, crop, ordering)

        # ========== Dukkakli ilovasi==========

        fifth_forest_app = create_column(statement_forest_add, None, "Дуккакли-ilovasi", "1")

        fifth_title_forest = create_column(
            statement_forest_add,
            fifth_forest_app,
            "Агентлик тизимидаги хўжаликларда 2025 йилда Дуккакли экинларни экилиши ва махсулотларини етиштириш"
            " тўғрисида, Маълумот",
            "1.1"
        )

        create_column(statement_forest_add, fifth_title_forest, "Хўжалик номи", "1.1.1", is_organization=True)

        dukkakli_ekinlar = create_column(statement_forest_add, fifth_title_forest, "Дуккакли", "1.1.2")

        create_triplet(statement_forest_add, dukkakli_ekinlar, "1.1.2")

        jumlalardan = create_column(statement_forest_add, fifth_title_forest, "Шу жумладан", "1.1.3")

        dukkakli_crops = [
            ("Нухат", "1.1.3.1"),
            ("Мош", "1.1.3.2"),
            ("Ловия", "1.1.3.3"),
            ("Қизил ловия", "1.1.3.4"),
        ]
        for title, ordering in dukkakli_crops:
            crop = create_column(statement_forest_add, jumlalardan, title, ordering)
            create_triplet(statement_forest_add, crop, ordering)

        # ========== Ozuqa ilovasi==========

        sixth_forest_app = create_column(statement_forest_add, None, "Озуқа-ilovasi", "1")

        sixth_title_forest = create_column(
            statement_forest_add,
            sixth_forest_app,
            "Агентлик тизимидаги хўжаликларда 2025 йилда Озуқа экинларини экилиши ва махсулотларини етиштириш"
            " тўғрисида Маълумот",
            "1.1"
        )

        create_column(statement_forest_add, sixth_title_forest, "Хўжалик номи", "1.1.1", is_organization=True)

        ozuqali_ekinlar = create_column(statement_forest_add, sixth_title_forest, "Озуқа экинлар", "1.1.2")

        create_triplet(statement_forest_add, ozuqali_ekinlar, "1.1.2")

        shu_jumlalardan_ozuqa = create_column(statement_forest_add, sixth_title_forest, "Шу жумладан", "1.1.3")

        ozuqali_crops = [
            ("Маккажўхори (силос)", "1.1.3.1"),
            ("Беда", "1.1.3.2"),
            ("Сомон", "1.1.3.3"),
            ("Дағал хашак", "1.1.3.4"),
        ]
        for title, ordering in ozuqali_crops:
            crop = create_column(statement_forest_add, shu_jumlalardan_ozuqa, title, ordering)
            create_triplet(statement_forest_add, crop, ordering)

        suprug = create_column(statement_forest_add, sixth_title_forest, "Супурги", "1.1.4")

        suprug_children = [
            ("т/кў", "1.1.4.1"),
            ("м/кў", "1.1.4.2"),
            ("ц/кўм", "1.1.4.3"),
        ]

        for title, ordering in suprug_children:
            create_column(statement_forest_add, suprug, title, ordering)

        # ========== Bog`-Tog` ilovasi==========

        seventh_forest_app = create_column(statement_forest_add, None, "Боғ ва Ток-ilovasi", "1")

        seventh_title_forest = create_column(
            statement_forest_add,
            seventh_forest_app,
            "Агентлик тизимидаги хўжаликларда 2025 йилда Мевали боғ ва токзорлардан хўл мева ва узум етиштиришни кўпайтириш тўғрисида Маълумот",
            ordering="1.1"
        )

        create_column(statement_forest_add, seventh_title_forest, "Хўжаликлари номи", "1.1.1", is_organization=True)

        jami_bog_tok = create_column(statement_forest_add, seventh_title_forest, "Жами Боғ ва Токзорлар", "1.1.2")
        create_village(statement_forest_add, jami_bog_tok, "1.1.2")

        urugli = create_column(statement_forest_add, seventh_title_forest, "Уругли", "1.1.3")
        create_village(statement_forest_add, urugli, "1.1.3")

        shu_jumladan = create_column(statement_forest_add, seventh_title_forest, "Шу жумладан", "1.1.4")

        danakli = create_column(statement_forest_add, shu_jumladan, "Данакли", "1.1.4.1")
        create_village(statement_forest_add, danakli, "1.1.4.1")

        uzumzor = create_column(statement_forest_add, shu_jumladan, "Узумзор", "1.1.4.2")
        create_village(statement_forest_add, uzumzor, "1.1.4.2")

        create_column(statement_forest_add, seventh_title_forest, "2017-2024 йилдан кўчирилган боғлар", "1.1.5")

        # ========== Bodom va Pista ilovasi==========

        eighth_forest_app = create_column(statement_forest_add, None, "Бодом ва Писта-ilovasi", "1")

        eighth_title_forest = create_column(
            statement_forest_add,
            eighth_forest_app,
            "Агентлик тизимидаги хўжаликларда 2025 йилда Ёнғоқ мевали махсулотлар етиштириш тўғрисидаги Маълумот",
            ordering="1.1"
        )

        create_column(statement_forest_add, eighth_title_forest, "Ўрмон хўжаликлари номи", "1.1.1",
                      is_organization=True)

        jami_yongoq = create_column(statement_forest_add, eighth_title_forest, "Жами Ёнғоқ мевалилар", "1.1.2")
        create_village(statement_forest_add, jami_yongoq, "1.1.2")

        grek = create_column(statement_forest_add, eighth_title_forest, "Грек ёнғоғи", "1.1.3")
        create_village(statement_forest_add, grek, "1.1.3")

        bodom = create_column(statement_forest_add, eighth_title_forest, "Бодом", "1.1.4")
        create_village(statement_forest_add, bodom, "1.1.4")

        pista = create_column(statement_forest_add, eighth_title_forest, "Писта", "1.1.5")
        create_village(statement_forest_add, pista, "1.1.5")

        create_column(statement_forest_add, eighth_title_forest, "Табиий мевалар тайёрлаш, тн", "1.1.6")


        self.stdout.write(
            self.style.SUCCESS("✅ Successfully created 'Qishloq xo`jaligi' Statement and Columns.")
        )
