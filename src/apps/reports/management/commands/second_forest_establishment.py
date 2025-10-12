from django.core.management import BaseCommand
from django.utils import timezone

from apps.utils.services import PeriodChoices
from apps.reports.models import Statement, StatementColumn


def generate_tree_columns(statement, parent, ordering_prefix):
    for i, title in enumerate(["Nihol", "Ko‘chat"], start=1):
        sub = StatementColumn.objects.create(
            statement=statement,
            parent=parent,
            title_uz=title,
            title_ru={"Nihol": "Саженцы", "Ko‘chat": "Ростки"}[title],
            ordering=f"{ordering_prefix}.{i}"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=sub,
            title_uz="Reja",
            title_ru="План",
            ordering=f"{ordering_prefix}.{i}.1",
            status_plan=StatementColumn.PlanStatus.YILLIK
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=sub,
            title_uz="Amalda",
            title_ru="Факт",
            ordering=f"{ordering_prefix}.{i}.2"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=sub,
            title_uz="Foiz",
            title_ru="Процент",
            ordering=f"{ordering_prefix}.{i}.3",
            is_user_input=False
        )


def generate_grouped_subtree(statement, parent, ordering_prefix, section_title_uz=None, section_title_ru=None,
                             is_user_input=True):
    if section_title_uz and section_title_ru:
        parent = StatementColumn.objects.create(
            statement=statement,
            parent=parent,
            title_uz=section_title_uz,
            title_ru=section_title_ru,
            ordering=ordering_prefix,
            is_user_input=is_user_input
        )
        ordering_prefix += ".1"

    StatementColumn.objects.create(
        statement=statement,
        parent=parent,
        title_uz="jami ming dona",
        title_ru="всего тысяч штук",
        ordering=f"{ordering_prefix}.1",
        is_user_input=False
    )
    sub = StatementColumn.objects.create(
        statement=statement,
        parent=parent,
        title_uz="shu jumladan",
        title_ru="в том числе",
        ordering=f"{ordering_prefix}.2"
    )
    StatementColumn.objects.create(
        statement=statement,
        parent=sub,
        title_uz="nihol",
        title_ru="саженцы",
        ordering=f"{ordering_prefix}.2.1"
    )
    StatementColumn.objects.create(
        statement=statement,
        parent=sub,
        title_uz="ko‘chat",
        title_ru="ростки",
        ordering=f"{ordering_prefix}.2.2"
    )


class Command(BaseCommand):
    def handle(self, *args, **options):
        # ==========================================================================  Qalamcha tayyorlash
        current_year = timezone.now().strftime("%Y")

        parent_statement = Statement.objects.get(
            name_uz="O'rmon barpo qilish",
            name_ru="Создание леса",
        )

        statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Qalamcha tayyorlash",
            name_ru="Подготовка черенков",
            period=PeriodChoices.YILLIK
        )

        app_column = StatementColumn.objects.create(
            statement=statement,
            title_uz="4-ilova",
            title_ru="Приложение 4",
            ordering="1"
        )

        title_column_1 = StatementColumn.objects.create(
            statement=statement,
            parent=app_column,
            title_uz=f"O‘rmon xo‘jaliklari tomonidan {current_year} yil bahor mavsumlarida qalamchalar tayyorlash bo‘yicha tezkor ma‘lumot.",
            title_ru=f"Срочная информация о подготовке черенков лесничествами в весенние сезоны {current_year} года.",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=statement,
            parent=title_column_1,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )

        parent_1 = StatementColumn.objects.create(
            statement=statement,
            parent=title_column_1,
            title_uz="Qalamchalar tayyorlash jami",
            title_ru="Всего подготовка черенков",
            ordering="1.1.2",
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=parent_1,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.2.1",
            status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL,
            is_user_input=True
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=parent_1,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.2.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=parent_1,
            title_uz="Foiz",
            title_ru="Процент",
            ordering="1.1.2.3",
            is_user_input=False
        )

        tree_group_column = StatementColumn.objects.create(
            statement=statement,
            parent=title_column_1,
            title_uz="Shu jumladan: daraxt turlari bo‘yicha",
            title_ru="В том числе: по видам деревьев",
            ordering="1.1.3"
        )

        daraxt_turlari = [
            "Terak",
            "Jiyda",
            "Chinar",
            "majnutol",
            "tol",
            "Xilokatalpa",
            "Lavanda",
            "Atirgul",
            "Namatak",
            "Boshqa turlar"
        ]
        daraxt_turlari_ru = [
            "Тополь",
            "Ясень",
            "Тополь",
            "Маджунус",
            "Ива",
            "Гибридная катальпа",
            "Лаванда",
            "Роза",
            "Шиповник",
            "Другие виды"
        ]

        for i, (tree_name_uz, tree_name_ru) in enumerate(zip(daraxt_turlari, daraxt_turlari_ru), start=1):
            tree_ordering = f"1.1.3.{i}"
            StatementColumn.objects.create(
                statement=statement,
                parent=tree_group_column,
                title_uz=tree_name_uz,
                title_ru=tree_name_ru,
                ordering=tree_ordering
            )


        # ==========================================================================  Ko‘chat va Nihol

        third_statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Ko‘chat va Nihol",
            name_ru="Ростки и саженцы",
            period=PeriodChoices.YILLIK
        )

        app_column = StatementColumn.objects.create(
            statement=third_statement,
            title_uz="Ko‘chat-va-Nihol-ilova",
            title_ru="Приложение Ростки-и-Саженцы",
            ordering="3",
        )

        title_column_2 = StatementColumn.objects.create(
            statement=third_statement,
            parent=app_column,
            title_uz="O‘rmon xo‘jaligi davlat qo‘mitasi tizimidagi o‘rmon xo‘jaliklariida niholxona va ko‘chatxonalar tashkil etish, yillik nihol va ko‘chat yetishtirish harakati to‘g‘risida umumlashtirilgan ma‘lumot",
            title_ru="Обобщенная информация о создании питомников и теплиц, а также ежегодном выращивании саженцев и ростков в лесничествах системы Государственного комитета лесного хозяйства",
            ordering="3.1",
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=title_column_2,
            title_uz="Tashkilot nomi",
            title_ru="Названия хозяйств",
            ordering="3.1.1",
            is_organization=True,
        )

        generate_grouped_subtree(
            third_statement,
            title_column_2,
            "3.1.3",
            "Yil boshiga bo'lgan qoldiq",
            "Осталось до начала года",
            is_user_input=False
        )

        generate_grouped_subtree(
            third_statement,
            title_column_2,
            "3.1.4",
            "Shu jumladan: Joriy yilda yetishtirilgan nihol, qalamcha va ko‘chatlar (shkolka)",
            "В том числе: Саженцы, черенки и саженцы, выращенные в текущем году (школка)",
            is_user_input=False
        )

        generate_grouped_subtree(
            third_statement,
            title_column_2,
            "3.1.5",
            "Sotib olindi",
            "Куплено",
            is_user_input=False
        )

        generate_grouped_subtree(
            third_statement,
            title_column_2,
            "3.1.6",
            "Boshqa tashkilotlardan beg'araz olindi",
            "Безвозмездно получено от других организаций",
            is_user_input=False
        )

        generate_grouped_subtree(
            third_statement,
            title_column_2,
            "3.1.7",
            "Jami yetishtirildi (inventarizatsiya)",
            "Всего произведено (инвентаризация)",
            is_user_input=False
        )

        sarflanishi = StatementColumn.objects.create(
            statement=third_statement,
            parent=title_column_2,
            title_uz="SARFLANISHI",
            title_ru="ИЗРАСХОДОВАНИЕ",
            ordering="3.1.8",
            is_user_input=False
        )

        categories = [
            ("O‘rmon barpo qilishga", "3.1.9", "Для создания лесов"),
            ("O‘rmonlarni xatosiga ekildi", "3.1.10", "Для восполнения потерь лесов"),
            ("Ko‘kalamzorlashtirish tadbirlari uchun", "3.1.11", "Для мероприятий по озеленению"),
            ("Beg‘araz berildi", "3.1.12", "Передано бесплатно"),
            ("Sotildi", "3.1.13", "Продано"),
            ("Tarbiya bo‘limiga o‘tkazildi", "3.1.14", "Передано в питомник"),
            ("Nobud bo‘lgan nihollar (buyruq asosida)", "3.1.15", "Уничтоженные саженцы (на основании приказа)")
        ]

        for title_uz, prefix, title_ru in categories:
            parent = StatementColumn.objects.create(
                statement=third_statement,
                parent=sarflanishi,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=prefix,
                is_user_input=False
            )
            generate_grouped_subtree(third_statement, parent, prefix, is_user_input=False)

        generate_grouped_subtree(
            third_statement,
            title_column_2,
            "3.1.16",
            "Jami sarflangan",
            "Всего потрачено",
            is_user_input=False
        )

        generate_grouped_subtree(
            third_statement,
            title_column_2,
            "3.1.17",
            "Shu davrga nisbatan yakuniy qoldiq",
            "Итоговый остаток за тот же период",
            is_user_input=False
        )

        # ==========================================================================  Ko‘chat

        app_kochat_column = StatementColumn.objects.create(
            statement=third_statement,
            title_uz="Ko‘chat-ilovasi",
            title_ru="Приложение Ростки",
            ordering="1"
        )

        title_column_kochat = StatementColumn.objects.create(
            statement=third_statement,
            parent=app_kochat_column,
            title_uz="O‘rmon xo‘jaligida ko‘chatxonaning tarbiya bo‘limida mavjud ko‘chatlar harakati to‘g‘risida",
            title_ru="О движении ростков в питомнике лесного хозяйства",
            ordering="1.1"
        )

        data_structure = [
            ("Tashkilot nomi", "1.1.1", [], True),
            ("Yil boshiga qoldiq", "1.1.2", []),
            ("Kirim", "1.1.3", [
                ("Joriy yilda yetishtirilgan qalamcha va ko‘chatlar (shkolka)", "1.1.3.1"),
                ("Sotib olindi", "1.1.3.2"),
                ("Boshqa tashkilotlardan beg‘araz olindi", "1.1.3.3")
            ]),
            ("Jami yetishtirildi (inventarizatsiya)", "1.1.4", []),
            ("Chiqim", "1.1.5", [
                ("O‘rmon barpo qilindi", "1.1.5.1"),
                ("O‘rmon xatosiga ekildi", "1.1.5.2"),
                ("Ko‘kalamzorlashtirish tadbirlari uchun", "1.1.5.3"),
                ("Tarbiya bo`limiga o`tkalizdi", "1.1.5.4"),
                ("Sotildi", "1.1.5.5", [
                    ("Ko'chatlar", "1.1.5.5.1"),
                    ("shartnoma raqami (№ sanasi)", "1.1.5.5.2"),
                    ("Ko`chat soni", "1.1.5.5.3"),
                    ("summasi", "1.1.5.5.4")
                ]),
                ("Beg`araz berildi", "1.1.5.6", [
                    ("ko‘chat soni, (dona)", "1.1.5.6.1"),
                    ("summasi (ming so‘m)", "1.1.5.6.2")
                ]),
                ("Nobud bo‘lgan ko‘chatlar (buyruq asosida)", "1.1.5.7"),
                ("Jami chiqim", "1.1.5.8"),
                ("Shu davrga nisbatan yakuniy qoldiq", "1.1.5.9"),
            ])
        ]

        def create_columns(parent, structure):
            for title_uz, ordering, *rest in structure:
                children = rest[0] if rest else []
                is_organization = rest[1] if len(rest) == 2 else False
                title_ru = {
                    "Tashkilot nomi": "Название организации",
                    "Yil boshiga qoldiq": "Остаток на начало года",
                    "Kirim": "Приход",
                    "Joriy yilda yetishtirilgan qalamcha va ko‘chatlar (shkolka)": "Выращенные черенки и ростки в текущем году (школка)",
                    "Sotib olindi": "Приобретено",
                    "Boshqa tashkilotlardan beg‘araz olindi": "Получено бесплатно от других организаций",
                    "Jami yetishtirildi (inventarizatsiya)": "Всего выращено (инвентаризация)",
                    "Chiqim": "Расход",
                    "O‘rmon barpo qilindi": "Создание лесов",
                    "O‘rmon xatosiga ekildi": "Посадка для восполнения потерь лесов",
                    "Ko‘kalamzorlashtirish tadbirlari uchun": "Для мероприятий по озеленению",
                    "Tarbiya bo`limiga o`tkalizdi": "Передано в Департамент образования",
                    "Sotildi": "Продано",
                    "Ko'chatlar": "Ростки",
                    "shartnoma raqami (№ sanasi)": "Номер договора (дата)",
                    "ko‘chat soni, (dona)": "Количество ростков (шт)",
                    "summasi (ming so‘m)": "Сумма (тыс. сум)",
                    "Beg`araz berildi": "Бескорыстно",
                    "Nobud bo‘lgan ko‘chatlar (buyruq asosida)": "Уничтоженные ростки (на основании приказа)",
                    "Jami chiqim": "Общий расход",
                    "Shu davrga nisbatan yakuniy qoldiq": "Итоговый остаток за период"
                }.get(title_uz, title_uz)

                is_input = False if title_uz in (
                    "Jami yetishtirildi (inventarizatsiya)",
                    "Jami chiqim",
                    "Shu davrga nisbatan yakuniy qoldiq"
                ) else True

                col = StatementColumn.objects.create(
                    statement=third_statement,
                    parent=parent,
                    title_uz=title_uz,
                    title_ru=title_ru,
                    ordering=ordering,
                    is_organization=is_organization,
                    is_user_input=is_input
                )
                if children:
                    create_columns(col, children)

        create_columns(title_column_kochat, data_structure)

        # ==========================================================================  Nihol

        app_nihol_column = StatementColumn.objects.create(
            statement=third_statement,
            title_uz="Nihol-ilovasi",
            title_ru="Приложение Саженцы",
            ordering="2"
        )

        title_column_nihol = StatementColumn.objects.create(
            statement=third_statement,
            parent=app_nihol_column,
            title_uz="O‘rmon xo‘jaligida ko‘chatxonaning tarbiya bo‘limida mavjud nihollar harakati to‘g‘risida",
            title_ru="О движении саженцев в питомнике лесного хозяйства",
            ordering="2.1"
        )

        data_structure = [
            ("Tashkilot nomi", "2.1.1", [], True),
            ("Yil boshiga qoldiq", "2.1.2", []),
            ("Kirim", "2.1.3", [
                ("Joriy yilda yetishtirilgan qalamcha va nihollar (shkolka)", "2.1.3.1"),
                ("Sotib olindi", "2.1.3.2"),
                ("Boshqa tashkilotlardan beg‘araz olindi", "2.1.3.3")
            ]),
            ("Jami yetishtirildi (inventarizatsiya)", "2.1.4", []),
            ("Chiqim", "2.1.5", [
                ("O‘rmon barpo qilindi", "2.1.5.1"),
                ("O‘rmon xatosiga ekildi", "2.1.5.2"),
                ("Ko‘kalamzorlashtirish tadbirlari uchun", "2.1.5.3"),
                ("Tarbiya bo`limiga o`tkalizdi", "2.1.5.4"),
                ("Sotildi", "2.1.5.5", [
                    ("Nihollar", "2.1.5.5.1"),
                    ("shartnoma raqami (№ sanasi)", "2.1.5.5.2"),
                    ("nihol soni", "2.1.5.5.3"),
                    ("summasi", "2.1.5.5.4")
                ]),
                ("Beg`araz sotildi", "2.1.5.6", [
                    ("nihollari soni, (dona)", "2.1.5.6.1"),
                    ("summasi (ming so‘m)", "2.1.5.6.2")
                ]),
                ("Nobud bo‘lgan nihollar (buyruq asosida)", "2.1.5.7"),
                ("Jami chiqim", "2.1.5.8"),
                ("Shu davrga nisbatan yakuniy qoldiq", "2.1.5.9"),
            ])
        ]

        def create_columns(parent, structure):
            for title_uz, ordering, *rest in structure:
                children = rest[0] if rest else []
                is_organization = rest[1] if len(rest) == 2 else False

                # Ruscha tarjimalar lug‘ati
                title_ru = {
                    "Tashkilot nomi": "Название организации ",
                    "Yil boshiga qoldiq": "Остаток на начало года",
                    "Kirim": "Приход",
                    "Joriy yilda yetishtirilgan qalamcha va nihollar (shkolka)": "Выращенные черенки и саженцы в текущем году (школка)",
                    "Sotib olindi": "Приобретено",
                    "Boshqa tashkilotlardan beg‘araz olindi": "Получено бесплатно от других организаций",
                    "Jami yetishtirildi (inventarizatsiya)": "Всего выращено (инвентаризация)",
                    "Chiqim": "Расход",
                    "O‘rmon barpo qilindi": "Создание лесов",
                    "O‘rmon xatosiga ekildi": "Посадка для восполнения потерь лесов",
                    "Ko‘kalamzorlashtirish tadbirlari uchun": "Для мероприятий по озеленению",
                    "Tarbiya bo`limiga o`tkalizdi": "Передано в Департамент образования",
                    "Sotildi": "Продано",
                    "Nihollar": "Саженцы",
                    "shartnoma raqami (№ sanasi)": "Номер договора (дата)",
                    "nihollari soni, (dona)": "Количество саженцев (шт)",
                    "summasi (ming so‘m)": "Сумма (тыс. сум)",
                    "Beg`araz berildi:": "Бескорыстно",
                    "Nobud bo‘lgan nihollar (buyruq asosida)": "Уничтоженные саженцы (на основании приказа)",
                    "Jami chiqim": "Общий расход",
                    "Shu davrga nisbatan yakuniy qoldiq": "Итоговый остаток за период"
                }.get(title_uz, title_uz)

                # ✅ Faqat 3ta maxsus ustun uchun is_user_input=False
                is_input = False if title_uz in (
                    "Jami yetishtirildi (inventarizatsiya)",
                    "Jami chiqim",
                    "Shu davrga nisbatan yakuniy qoldiq"
                ) else True

                col = StatementColumn.objects.create(
                    statement=third_statement,
                    parent=parent,
                    title_uz=title_uz,
                    title_ru=title_ru,
                    ordering=ordering,
                    is_organization=is_organization,
                    is_user_input=is_input
                )

                if children:
                    create_columns(col, children)

        create_columns(title_column_nihol, data_structure)


        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Подготовка черенков' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Ростки' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Саженцы' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Ростки и саженцы' statement."))