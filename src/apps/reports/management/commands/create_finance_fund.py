from django.core.management.base import BaseCommand
from apps.reports.models import Statement, StatementColumn
from django.db import transaction
from apps.utils.services import PeriodChoices

class Command(BaseCommand):
    help = "Create Daromad statement structure (income statement with all sections)"

    def handle(self, *args, **kwargs):
        Statement.objects.filter(name="Jamg'arma").delete()
        with transaction.atomic():
            moliya_statement = Statement.objects.get(
                name="Moliya-iqtisod va buxgalteriya",
            )
            daromad_statement = Statement.objects.create(
                name="Jamg'arma",
                parent=moliya_statement,
                period=PeriodChoices.HAFTALIK
            )
            info = StatementColumn.objects.create(
                statement=daromad_statement,
                title="2025 yil davomida topilgan daromadlar haqida MA'LUMOT",
                ordering="1"
            )
            info = StatementColumn.objects.create(
                statement=daromad_statement,
                title="Tashkilot nomi",
                ordering="1.1"
            )

            # Income types
            income_types = [
                ("Ruxsatnoma olish uchun arizalarni ko‘rib chiqganlik va ruxsatnomalar berganlik uchun tushgan mablag‘ (1001)", "1.2"),
                ("Hayvonot va o‘simlik dunyosiga yetkazilgan zarar o‘rnini qoplash bo‘yicha undirilgan mablag‘ (1007)", "1.3"),
                ("Ruxsat etilgan hududlarda ovchilik qilish uchun tushgan mablag‘ (50%)", "1.4"),
                ("Ummon fondi yerlaridagi boyliklar va madaniy meroslardan foydalanishdan tushgan mablag‘ (100%)", "1.5"),
                ("Ummon xo‘jaligi yog‘och kesishdan tushgan mablag‘ (50%)", "1.6"),
                ("Boshqa daromadlar (101)", "1.7"),
            ]

            for idx, (income_title, income_order) in enumerate(income_types, start=1):
                income_node = StatementColumn.objects.create(
                    parent=info,
                    statement=daromad_statement,
                    title=income_title,
                    ordering=income_order
                )

                # Subnodes: Jami tushum + shundan jamg’armaga -> To‘lanishi kerak, To‘landi, Qoldiq
                jami_node = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=income_node,
                    title="Jami tushum",
                    ordering=f"{income_order}.1"
                )

                jamg_node = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=income_node,
                    title="shundan jamg’armaga",
                    ordering=f"{income_order}.2"
                )

                for j_idx, title in enumerate(["To‘lanishi kerak (100%)", "To‘landi", "Qoldiq"], start=1):
                    StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=jamg_node,
                        title=title,
                        ordering=f"{income_order}.2.{j_idx}"
                    )

            jami_tushum = StatementColumn.objects.create(
                statement=daromad_statement,
                title="Jami tushum",
                ordering="1.10"
            )

            # Jamg’arma jami tushum
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=jami_tushum,
                title="Jamg’arma ga jami tushum",
                ordering="1.10.1"
            )

            jamg_shundan = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=jami_tushum,
                title="shundan jamg’armaga",
                ordering="1.10.2"
            )

            for j_idx, title in enumerate([
                "Jamg’arma ga tushishi kerak bo‘lgan tushum",
                "To‘landi",
                "Qoldiq"
            ], start=1):
                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=jamg_shundan,
                    title=title,
                    ordering=f"1.10.2.{j_idx}"
                )

        self.stdout.write(self.style.SUCCESS("✅ Daromad statement yaratildi."))
