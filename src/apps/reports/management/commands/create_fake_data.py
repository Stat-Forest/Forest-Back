from django.core.management.base import BaseCommand
from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = 'Creates Daromad statement and associated statement columns'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚧 Daromad statement column seeding started...")

        try:
            # 1. Get or create parent statement: "Moliya-iqsisod va bugaltiriya"
            parent_stmt, _ = Statement.objects.get_or_create(name="Moliya-iqsisod va bugaltiriya", parent=None)

            # 2. Create "Daromad" statement under "Moliya-iqsisod va bugaltiriya"
            daromad_stmt, _ = Statement.objects.get_or_create(
                name="Daromad",
                parent=parent_stmt,
                period=PeriodChoices.CHORAKLIK
            )

            # 3. Create 3 parent-level columns
            column_titles = ["Daromad turlari bo‘yicha", "Tushumlar bo‘yicha", "Svod"]
            column_parents = {}
            for idx, title in enumerate(column_titles, start=1):
                col, _ = StatementColumn.objects.get_or_create(
                    statement=daromad_stmt,
                    title=title,
                    ordering=idx
                )
                column_parents[title] = col

            # 4. Create child column under "Daromad turlari bo‘yicha"
            info_title = "O‘rmon xo‘jaligi agentligi tizimidagi tashkilotlarining 2025 yil davomida topilgan daromadlari to‘g‘risida MA'LUMOT"
            info_col, _ = StatementColumn.objects.get_or_create(
                statement=daromad_stmt,
                title=info_title,
                ordering=4,
                parent=column_parents["Daromad turlari bo‘yicha"]
            )

            # 5. Create 19 sub-columns under the info_col
            sub_titles = [
                "Xo‘jalik nomi",
                "Ko‘chat va nihol sotish",
                "Yog‘och o‘tin sotish",
                "Sanoat, xalq iste’mol mollari",
                "Aholiga pullik xizmat",
                "Yaylov tushumi",
                "Qishloq xo‘jaligi mahsulotlari",
                "Chorvachilik",
                "Parrandachilik",
                "Quyonchilik",
                "Baliqchilik",
                "Asalarichilik",
                "Dorivor o‘simliklar",
                "Ko‘kalamzorlashtirish",
                "Boshqa tushumlar",
                "Ixota",
                "Urug‘ sotishdan",
                "Ijara to‘lovlari",
                "Jami"
            ]
            for idx, title in enumerate(sub_titles, start=1):
                StatementColumn.objects.get_or_create(
                    statement=daromad_stmt,
                    title=title,
                    ordering=100 + idx,
                    parent=info_col
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("✅ Daromad statement columns created successfully!"))
