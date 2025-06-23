from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    def handle(self, *args, **options):
    # ====================================================  Qishloq Xo`jaligi - Boshoqli Don
        def create_column(statement, parent, title, ordering):
            return StatementColumn.objects.create(
                statement=statement,
                parent=parent,
                title=title,
                ordering=ordering
            )

        def create_triplet(statement, parent, base_ordering):
            for i, title in enumerate(["га", "ц/га", "тн"], start=1):
                create_column(statement, parent, title, f"{base_ordering}.{i}")

        forest_add = Statement.objects.create(parent=None, name="O`rmonlardan qo`shimcha foydalanish")
        statement_forest_add = Statement.objects.create(parent=forest_add, name="Qishloq xo`jaligi")

        forest_app = create_column(statement_forest_add, None, "Boshokli don", "1")

        title_forest_app = create_column(
            statement_forest_add,
            forest_app,
            "Агентлик тизимидаги хўжаликларда 2025 йилда бошоқли дон экинларини экиш ва махсулотларини етиштириш тўғрисида Маълумот",
            "1.1"
        )

        create_column(statement_forest_add, title_forest_app, "Хўжалик номи", "1.1.1")

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
    # ====================================================  Qishloq Xo`jaligi - Sabzavot








        self.stdout.write(
            self.style.SUCCESS("✅ Successfully created 'Qishloq xo`jaligi' Statement and Columns."))