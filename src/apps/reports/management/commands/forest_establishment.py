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
        second_statement = Statement.objects.create(
            parent=first_statement,
            name="Yopiq ildiz yirik hajmli"
        )

        app_column = StatementColumn.objects.create(
            statement=second_statement,
            parent=None,
            title="1-ilova",
            ordering="1"
        )

        title_column = StatementColumn.objects.create(
            statement=second_statement,
            parent=app_column,
            title=(
                "O`rmon xo`jaligi agentligi tizimidagi o`rmon xo`jaliklari tomonidan "
                "2025 yildan yirik hajmli yopiq ko`chatlarini yetishtirish to`g`risida "
                "tezkor ma`lumot."
            ),
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=second_statement,
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
                statement=second_statement,
                parent=title_column,
                title=title,
                ordering=parent_ordering
            )
            for i, child in enumerate(children, start=1):
                StatementColumn.objects.create(
                    statement=second_statement,
                    parent=parent,
                    title=child,
                    ordering=f"{parent_ordering}.{i}",
                    is_plan=(child.lower() == "reja")
                )

        # ================================================================

        second_statement = Statement.objects.create(
            parent=first_statement,
            name="O`rmon barpo qilish bo`limi"
        )

        # 2-ilova sarlavhasi (StatementColumn)
        second_app_column = StatementColumn.objects.create(
            statement=second_statement,
            parent=None,
            title="2-ilova",
            ordering="1"
        )

        # 2-ilovadagi bosh mavzu sarlavhasi
        second_ilova_title = StatementColumn.objects.create(
            statement=second_statement,
            parent=second_app_column,
            title="O`rmon xo`jaliklari tomonidan joriy yilda o`rmon barpo etilishi to`g`risida ma`lumot",
            ordering="1.1"
        )

        organization_name = StatementColumn.objects.create(
            statement=second_statement,
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
                statement=second_statement,
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
                        statement=second_statement,
                        parent=parent_column,
                        title=child,
                        ordering=f"{ordering_base}.{i}.{j}"
                    )
            elif has_subcolumns:
                for j, sub in enumerate(["Reja", "Amalda", "Foiz"], start=1):
                    StatementColumn.objects.create(
                        statement=second_statement,
                        parent=parent_column,
                        title=sub,
                        ordering=f"{ordering_base}.{i}.{j}",
                        is_plan=(sub == "Reja")
                    )


        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'O`rmon barpo qilish' Statement and Columns."))
