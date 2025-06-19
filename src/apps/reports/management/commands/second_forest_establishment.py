from django.core.management import BaseCommand

from apps.utils.services import PeriodChoices
from apps.reports.models import Statement, StatementColumn


def generate_tree_columns(statement, parent, ordering_prefix):
    for i, title in enumerate(["Ниҳол", "Кўчат"], start=1):
        sub = StatementColumn.objects.create(
            statement=statement,
            parent=parent,
            title=title,
            ordering=f"{ordering_prefix}.{i}"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=sub,
            title="Режа",
            ordering=f"{ordering_prefix}.{i}.1",
            status_plan=StatementColumn.PlanStatus.YILLIK
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=sub,
            title="Амалда",
            ordering=f"{ordering_prefix}.{i}.2"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=sub,
            title="Фоиз",
            ordering=f"{ordering_prefix}.{i}.3"
        )


def generate_grouped_subtree(statement, parent, ordering_prefix):
    StatementColumn.objects.create(
        statement=statement,
        parent=parent,
        title="жами минг дона",
        ordering=f"{ordering_prefix}.1"
    )
    sub = StatementColumn.objects.create(
        statement=statement,
        parent=parent,
        title="шу жумладан",
        ordering=f"{ordering_prefix}.2"
    )
    StatementColumn.objects.create(
        statement=statement,
        parent=sub,
        title="нихол",
        ordering=f"{ordering_prefix}.2.1"
    )
    StatementColumn.objects.create(
        statement=statement,
        parent=sub,
        title="кучат",
        ordering=f"{ordering_prefix}.2.2"
    )


class Command(BaseCommand):
    def handle(self, *args, **options):
        # ==========================================================================  Qalamcha tayyorlash

        parent_statement = Statement.objects.get(name="O`rmon barpo qilish")

        statement = Statement.objects.create(
            parent=parent_statement,
            name="Қаламча тайёрлаш",
            period=PeriodChoices.YILLIK
        )

        app_column = StatementColumn.objects.create(
            statement=statement,
            title="4-ilova",
            ordering="1"
        )

        title_column_1 = StatementColumn.objects.create(
            statement=statement,
            parent=app_column,
            title="Ўрмон хўжаликлари томонидан 2025 йил баҳор мавсумларида қаламчалар тайёрлаш бўйича тезкор маълумот.",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=statement,
            parent=title_column_1,
            title="Ҳудудлар номланиши",
            ordering="1.1.1",
            is_organization=True
        )

        parent_1 = StatementColumn.objects.create(
            statement=statement,
            parent=title_column_1,
            title="Қаламчалар тайёрлаш жами",
            ordering="1.1.2"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=parent_1,
            title="Режа",
            ordering="1.1.2.1",
            status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=parent_1,
            title="Амалда",
            ordering="1.1.2.2"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=parent_1,
            title="Фоиз",
            ordering="1.1.2.3"
        )

        tree_group_column = StatementColumn.objects.create(
            statement=statement,
            parent=title_column_1,
            title="Шу жумладан: дарахт турлари бўйича",
            ordering="1.1.3"
        )

        daraxt_turlari = [
            "Терак",
            "Жийда",
            "Чинор",
            "мажнунтол",
            "тол",
            "Хилокатальпа",
            "Бошқа турлар"
        ]

        for i, tree_name in enumerate(daraxt_turlari, start=1):
            tree_ordering = f"1.1.3.{i}"
            tree_column = StatementColumn.objects.create(
                statement=statement,
                parent=tree_group_column,
                title=tree_name,
                ordering=tree_ordering
            )
            StatementColumn.objects.create(
                statement=statement,
                parent=tree_column,
                title="Режа",
                ordering=f"{tree_ordering}.1",
                status_plan=StatementColumn.PlanStatus.YILLIK
            )
            StatementColumn.objects.create(
                statement=statement,
                parent=tree_column,
                title="Амалда",
                ordering=f"{tree_ordering}.2"
            )

        # ==========================================================================  Ko`chat va Nihol

        third_statement = Statement.objects.create(
            parent=parent_statement,
            name="Ko‘chat va Nihol",
            period=PeriodChoices.YILLIK
        )

        app_column = StatementColumn.objects.create(
            statement=third_statement, title="Ko`chat-va-Nihol-ilova", ordering="1"
        )

        title_column_2 = StatementColumn.objects.create(
            statement=third_statement,
            parent=app_column,
            title="Ўрмон хўжалиги давлат қўмитаси тизимидаги ўрмон хўжаликларида  ниҳолхона ва кўчатхоналар ташкил этиш, йиллик ниҳол ва кўчат етиштириш ҳаракати тўғрисида умумлашган маълумот",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=third_statement, parent=title_column_2, title="Хўжаликлар номи", ordering="1.1.1",
            is_organization=True
        )

        jami = StatementColumn.objects.create(
            statement=third_statement, parent=title_column_2, title="Жами ниҳолхона ва кўчатхоналар ташкил этиш (га)",
            ordering="1.1.2"
        )
        StatementColumn.objects.create(statement=third_statement, parent=jami, title="Режа", ordering="1.1.2.1",
                                       status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL)
        StatementColumn.objects.create(statement=third_statement, parent=jami, title="Амалда", ordering="1.1.2.2")
        StatementColumn.objects.create(statement=third_statement, parent=jami, title="Фоиз", ordering="1.1.2.3")

        subgroup = StatementColumn.objects.create(statement=third_statement, parent=title_column_2, title="шундан",
                                                  ordering="1.1.2.4")
        generate_tree_columns(third_statement, subgroup, "1.1.2.4")

        generate_grouped_subtree(third_statement, title_column_2, "1.1.3")
        generate_grouped_subtree(third_statement, title_column_2, "1.1.4")
        generate_grouped_subtree(third_statement, title_column_2, "1.1.5")
        generate_grouped_subtree(third_statement, title_column_2, "1.1.6")
        generate_grouped_subtree(third_statement, title_column_2, "1.1.7")

        sarflanishi = StatementColumn.objects.create(
            statement=third_statement, parent=title_column_2, title="САРФЛАНИШИ", ordering="1.1.8"
        )

        categories = [
            ("Ўрмон барпо килишга", "1.1.9"),
            ("Ўрмонларни хатосига экилди", "1.1.10"),
            ("Кўкаламзорлаштириш тадбирлари учун", "1.1.11"),
            ("Беғараз берилди", "1.1.12"),
            ("Сотилди", "1.1.13"),
            ("Тарбия бўлимига ўтказилди", "1.1.14"),
            ("Нобуд бўлган ниҳоллар (буйруқ асосида)", "1.1.15")
        ]

        for title, prefix in categories:
            parent = StatementColumn.objects.create(statement=third_statement, parent=sarflanishi, title=title,
                                                    ordering=prefix)
            generate_grouped_subtree(third_statement, parent, prefix)

        generate_grouped_subtree(third_statement, title_column_2, "1.1.16")

        # ==========================================================================  Ko`chat

        app_kochat_column = StatementColumn.objects.create(
            statement=third_statement,
            title="Ko`chat-ilovasi",
            ordering="1"
        )

        title_column_kochat = StatementColumn.objects.create(
            statement=third_statement,
            parent=app_kochat_column,
            title="Ўрмон хўжалигида кўчатхонанинг тарбия бўлимида мавжуд кўчатлар харакати тўғрисида",
            ordering="1.1"
        )

        data_structure = [
            ("Нихоллар", "1.1.1", [], True),
            ("Йил бошига қолдиқ", "1.1.2", []),
            ("Кирим", "1.1.3", [
                ("Жорий йилда етиштирилган қаламча ва кўчатлар (школка)", "1.1.3.1"),
                ("Сотиб олинди", "1.1.3.2"),
                ("Бошқа ташкилот-лардан беғараз олинди", "1.1.3.3")
            ]),
            ("Жами етиштирилди (инвентаризация)", "1.1.4", []),
            ("Чиқим", "1.1.5", [
                ("Ўрмон барпо қилинди", "1.1.5.1"),
                ("Ўрмон хатосига экилди", "1.1.5.2"),
                ("Кўкаламзорлаштириш тадбирлари учун", "1.1.5.3"),
                ("Тарбия бўлимига ўтказилди", "1.1.5.4"),
                ("Сотилди", "1.1.5.5", [
                    ("Ташкилот номи", "1.1.5.5.1"),
                    ("шартнома рақами (№ санаси)", "1.1.5.5.2"),
                    ("Ташкилот номи", "1.1.5.5.3"),
                    ("Ташкилот номи", "1.1.5.5.4")
                ]),
                ("Сотилди", "1.1.5.6", [
                    ("кўчат сони, (дона)", "1.1.5.6.1"),
                    ("суммаси (минг сўм)", "1.1.5.6.2")
                ]),
                ("Нобуд бўлган кўчатлар (буйруқ асосида)", "1.1.5.7"),
                ("Жами чиқим", "1.1.5.8"),
                ("Шу даврга нисбатан якуний қолдиқ", "1.1.5.9"),
            ])
        ]

        def create_columns(parent, structure):
            for title, ordering, *rest in structure:
                children = rest[0] if rest else []
                is_organization = rest[1] if len(rest) == 2 else False
                col = StatementColumn.objects.create(
                    statement=third_statement,
                    parent=parent,
                    title=title,
                    ordering=ordering,
                    is_organization=is_organization
                )
                if children:
                    create_columns(col, children)

        create_columns(title_column_kochat, data_structure)

        # ==========================================================================  Nihol

        app_nihol_column = StatementColumn.objects.create(
            statement=third_statement,
            title="Nihol-ilovasi",
            ordering="1"
        )

        title_column_nihol = StatementColumn.objects.create(
            statement=third_statement,
            parent=app_nihol_column,
            title="Ўрмон хўжалигида кўчатхонанинг тарбия бўлимида мавжуд кўчатлар харакати тўғрисида",
            ordering="1.1"
        )

        data_structure = [
            ("Нихоллар", "1.1.1", [], True),
            ("Йил бошига қолдиқ", "1.1.2", []),
            ("Кирим", "1.1.3", [
                ("Жорий йилда етиштирилган қаламча ва ниҳоллар (школка)", "1.1.3.1"),
                ("Сотиб олинди", "1.1.3.2"),
                ("Бошқа ташкилот-лардан беғараз олинди", "1.1.3.3")
            ]),
            ("Жами етиштирилди (инвентаризация)", "1.1.4", []),
            ("Чиқим", "1.1.5", [
                ("Ўрмон барпо қилинди", "1.1.5.1"),
                ("Ўрмон хатосига экилди", "1.1.5.2"),
                ("Кўкаламзорлаштириш тадбирлари учун", "1.1.5.3"),
                ("Тарбия бўлимига ўтказилди", "1.1.5.4"),
                ("Сотилди", "1.1.5.5", [
                    ("Ташкилот номи", "1.1.5.5.1"),
                    ("шартнома рақами (№ санаси)", "1.1.5.5.2"),
                    ("Ташкилот номи", "1.1.5.5.3"),
                    ("Ташкилот номи", "1.1.5.5.4")
                ]),
                ("Сотилди", "1.1.5.6", [
                    ("ниҳол сони, (дона)", "1.1.5.6.1"),
                    ("суммаси (минг сўм)", "1.1.5.6.2")
                ]),
                ("Нобуд бўлган ниҳоллар (буйруқ асосида)", "1.1.5.7"),
                ("Жами чиқим", "1.1.5.8"),
                ("Шу даврга нисбатан якуний қолдиқ", "1.1.5.9"),
            ])
        ]

        def create_columns(parent, structure):
            for title, ordering, *rest in structure:
                children = rest[0] if rest else []
                is_organization = rest[1] if len(rest) == 2 else False
                col = StatementColumn.objects.create(
                    statement=third_statement,
                    parent=parent,
                    title=title,
                    ordering=ordering,
                    is_organization=is_organization
                )
                if children:
                    create_columns(col, children)

        create_columns(title_column_nihol, data_structure)


        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Қаламча тайёрлаш' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Ko`chat' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Nihol' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Ko‘chat va Nihol' statement."))

