from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    help = "Create Statement Forest Establishment"

    def handle(self, *args, **options):
        Statement.objects.all().delete()
        StatementColumn.objects.all().delete()

        first_statement = Statement.objects.create(
            parent=None,
            name="O`rmon barpo qilish"
        )
        first_of_second_statement = Statement.objects.create(
            parent=first_statement,
            name="Yopiq ildiz yirik hajmli"
        )

        app_column = StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=None,
            title="1-ilova",
            ordering="1"
        )

        title_column = StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=app_column,
            title=(
                "O`rmon xo`jaligi agentligi tizimidagi o`rmon xo`jaliklari tomonidan "
                "2025 yildan yirik hajmli yopiq ko`chatlarini yetishtirish to`g`risida "
                "tezkor ma`lumot."
            ),
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=title_column,
            title="Xududlar nomi",
            ordering="1.1.1",
            is_organization=True
        )

        rows = [
            ("Yirik hajmli yopiq ildizli ko`chatlar yetishtirish miqdori", ["Reja", "Amalda", "Foiz"]),
            ("Tyanshan qoraqarag`ay", ["Reja", "Amalda"]),
            ("Tyanshan qarag`ayi", ["Reja", "Amalda"]),
            ("Vergin archa", ["Reja", "Amalda"]),
            ("Sharq tuya", ["Reja", "Amalda"]),
            ("Eldor qarag`ay", ["Reja", "Amalda"]),
            ("Krim qarag`ayi", ["Reja", "Amalda"]),
            ("Tuya sharq", ["Reja", "Amalda"]),
            ("Kiparis", ["Reja", "Amalda"]),
            ("Qayrag`och", ["Reja", "Amalda"]),
            ("Shumtol", ["Reja", "Amalda"]),
            ("Zarang", ["Reja", "Amalda"]),
            ("Sadaqayrog`och", ["Reja", "Amalda"]),
            ("Yapon saforasi", ["Reja", "Amalda"]),
            ("Akatsiya", ["Reja", "Amalda"]),
            ("Ipak Akatsiya", ["Reja", "Amalda"]),
            ("Aylant", ["Reja", "Amalda"]),
            ("Katalpa", ["Reja", "Amalda"]),
            ("Pavloniya", ["Reja", "Amalda"]),
            ("Chinor", ["Reja", "Amalda"]),
            ("Kashtan", ["Reja", "Amalda"]),
            ("Pisardi", ["Reja", "Amalda"]),
            ("Bag`ryannik", ["Reja", "Amalda"]),
            ("Chappa tut", ["Reja", "Amalda"]),
            ("Eman", ["Reja", "Amalda"]),
            ("Oqqayni", ["Reja", "Amalda"]),
            ("Boshqa turlar", ["Reja", "Amalda"]),
            ("Atirgul", ["Reja", "Amalda"]),
        ]

        for index, (title, children) in enumerate(rows, start=2):
            parent_ordering = f"1.1.{index}"
            parent = StatementColumn.objects.create(
                statement=first_of_second_statement,
                parent=title_column,
                title=title,
                ordering=parent_ordering
            )
            for i, child in enumerate(children, start=1):
                StatementColumn.objects.create(
                    statement=first_of_second_statement,
                    parent=parent,
                    title=child,
                    ordering=f"{parent_ordering}.{i}",
                    status_plan=(child.lower() == "reja")
                )

        # ================================================================ Yopiq ildiz yirik hajmli

        second_statement_of_forest = Statement.objects.create(
            parent=first_statement,
            name="O`rmon barpo qilish bo`limi"
        )

        # 2-ilova sarlavhasi (StatementColumn)
        second_app_column = StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=None,
            title="2-ilova",
            ordering="1"
        )

        # 2-ilovadagi bosh mavzu sarlavhasi
        second_ilova_title = StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=second_app_column,
            title="O`rmon xo`jaliklari tomonidan joriy yilda o`rmon barpo etilishi to`g`risida ma`lumot",
            ordering="1.1"
        )

        organization_name = StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=second_ilova_title,
            title="O`rmon xo`jaliklar nomi",
            ordering="1.1.1",
            is_organization=True
        )

        rows = [
            ("Jami", True),
            ("Cho‘l", True),
            ("Jami Yong‘oq Mevalar", True),
            ("Shundan", True),
            ("Jami tez o‘suvchilar", True),
            ("Shundan", False),  # Daraxt turlari
            ("Tabiiy tiklanishga ko‘maklashish va boshqa daraxt turlaridan ekish", False),
        ]

        ordering_base = "1.1"

        for i, (title, has_subcolumns) in enumerate(rows, start=2):
            parent_column = StatementColumn.objects.create(
                statement=second_statement_of_forest,
                parent=second_ilova_title,
                title=title,
                    ordering=f"{ordering_base}.{i}"
            )

            if title == "Shundan" and not has_subcolumns:
                children = [
                    "Terak",
                    "Pavloniya",
                    "Qayrog‘och",
                    "Shumtol",
                    "Chinor",
                    "Akatsiya",
                    "Boshqa turlar"
                ]
                for j, child in enumerate(children, start=1):
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_column,
                        title=child,
                        ordering=f"{ordering_base}.{i}.{j}"
                    )
            elif has_subcolumns:
                for j, sub in enumerate(["Reja", "Amalda", "Foiz"], start=1):
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_column,
                        title=sub,
                        ordering=f"{ordering_base}.{i}.{j}",
                        status_plan=StatementColumn.PlanStatus.YILLIK
                    )

        # ================================================================ Urug` Xarakai

        third_statement = Statement.objects.create(
            parent=first_statement,
            name="Urug` Xarakati"
        )

        third_app_column = StatementColumn.objects.create(
            statement=third_statement,
            title="3-ilova",
            ordering="1"
        )

        third_ilova_title = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_app_column,
            title="O`rmon xo`jaligida 2025 yilda tayyorlangan o`rmon daraxt va buta urug`larning xarakati to`g`risida",
            ordering="1.1"
        )

        third_organization_name = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Daraxt va buta urug`lari turlari",
            ordering="1.1.1"
        )

        first_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Urug` jamg`arish miqdori",
            ordering="1.1.2"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=first_column,
            title="Reja",
            ordering="1.1.2.1",
            status_plan=StatementColumn.PlanStatus.YILLIK
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=first_column,
            title="Amalda",
            ordering="1.1.2.2"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=first_column,
            title="Foiz",
            ordering="1.1.2.3"
        )

        yil_boshi_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Yil boshiga qoldiq",
            ordering="1.1.3"
        )

        hisobot_davri_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Hisobot davrida tayyorlandi va sotib olindi",
            ordering="1.1.4"
        )

        in_first_hisobot_davri_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot_davri_column,
            title="Xo`jalik tomonidan tayyorlandi",
            ordering="1.1.4.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_first_hisobot_davri_column,
            title="Jami",
            ordering="1.1.4.1.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_first_hisobot_davri_column,
            title="Sh.J urug`lik uchaskadan",
            ordering="1.1.4.1.2"
        )

        in_second_hisobot_davri_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot_davri_column,
            title="Boshqa tashkilotdan sotib olindi",
            ordering="1.1.4.2"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_second_hisobot_davri_column,
            title="Miqdori",
            ordering="1.1.4.2.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_second_hisobot_davri_column,
            title="Sarflangan summa",
            ordering="1.1.4.2.2"
        )

        hisobot_sarflandi_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Hisobot davrida sarflandi",
            ordering="1.1.5"
        )
        in_first_sarflandi_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot_sarflandi_column,
            title="Ko`chatzorlar barpo etish uchun",
            ordering="1.1.5.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_first_sarflandi_column,
            title="Miqdori (KG)",
            ordering="1.1.5.1.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_first_sarflandi_column,
            title="Ish hajmi (KG)",
            ordering="1.1.5.1.2"
        )

        in_second_sarflandi_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot_sarflandi_column,
            title="O`rmonzorlar barpo etish uchun",
            ordering="1.1.5.2"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_second_sarflandi_column,
            title="Miqdori (KG)",
            ordering="1.1.5.2.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_second_sarflandi_column,
            title="Ish Hajmi (KG)",
            ordering="1.1.5.2.2"
        )

        in_third_sarflandi_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot_sarflandi_column,
            title="O`rmonlarni hatosini to`ldirish uchun",
            ordering="1.1.5.3"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_third_sarflandi_column,
            title="Miqdori (KG)",
            ordering="1.1.5.3.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_third_sarflandi_column,
            title="Ish hajmi (KG)",
            ordering="1.1.5.3.2"
        )

        in_fourth_sarflandi_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot_sarflandi_column,
            title="Boshqa tashkilotlarga berildi",
            ordering="1.1.5.4"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_fourth_sarflandi_column,
            title="kg",
            ordering="1.1.5.4.1"
        )

        in_fifth_sarflandi_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot_sarflandi_column,
            title="Hisobdan chiqarildi",
            ordering="1.1.5.5"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=in_fifth_sarflandi_column,
            title="kg",
            ordering="1.1.5.5.1"
        )

        hisobot_ohiri_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title="Hisobot ohiriga qolgan qoldiq (kg)",
            ordering="1.1.6"
        )

        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'O`rmon barpo qilish' Statement and Columns."))
