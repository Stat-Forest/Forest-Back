from django.core.management import BaseCommand

from apps.reports.models import Statement, SumColumn
from apps.general.models import SumColumn


class Command(BaseCommand):
    help = "Create Yashil Makon Yig'ma SumColumns"

    def handle(self, *args, **options):

        def create_statement(parent, name_uz, name_ru):
            obj, _ = Statement.objects.get_or_create(
                parent=parent,
                name=name_uz,
                defaults={
                    "name_uz": name_uz,
                    "name_ru": name_ru,
                }
            )
            return obj

        def create_sum_column(statement, parent, title, ordering):
            obj, _ = SumColumn.objects.get_or_create(
                statement=statement,
                parent=parent,
                ordering=ordering,
                defaults={
                    "title": title,
                }
            )
            return obj

        # 1️⃣ Asosiy statement
        base_statement = Statement.objects.get(
            name_uz="Axborot-tahlil, ijro intizomi"
        )

        # 2️⃣ Yig'ma statement (doim bitta)
        yigma_statement = create_statement(
            parent=base_statement,
            name_uz="Yig'ma",
            name_ru="Сводный",
        )

        # 3️⃣ Root sum column
        yigma_ilovasi = create_sum_column(
            statement=yigma_statement,
            parent=None,
            title="Yig'ma ilovasi",
            ordering="1",
        )

        # 4️⃣ Asosiy sarlavha
        main_title = create_sum_column(
            yigma_statement,
            yigma_ilovasi,
            "O‘rmon agentligiga yuklatilgan muhim vazifalar ijrosi to‘g‘risida ma’lumoti",
            "1.1",
        )

        # 5️⃣ Chap ustunlar
        create_sum_column(yigma_statement, main_title, "Maqsadli ko‘rsatkich nomi", "1.1.1")
        create_sum_column(yigma_statement, main_title, "O‘lchov birligi", "1.1.2")
        create_sum_column(yigma_statement, main_title, "Yillik reja", "1.1.3")
        create_sum_column(yigma_statement, main_title, "Amalda", "1.1.4")

        bajarilishi = create_sum_column(
            yigma_statement,
            main_title,
            "Bajarilishi",
            "1.1.5",
        )

        create_sum_column(yigma_statement, bajarilishi, "Foizi", "1.1.5.1")
        create_sum_column(yigma_statement, bajarilishi, "Farqi (+;-)", "1.1.5.2")

        # 6️⃣ Hududlar
        regions = [
            "Qoraqalpog‘iston Respublikasi",
            "Andijon",
            "Buxoro",
            "Jizzax",
            "Qashqadaryo",
            "Navoiy",
            "Namangan",
            "Samarqand",
            "Surxondaryo",
            "Sirdaryo",
            "Toshkent viloyati",
            "Farg‘ona",
            "Xorazm",
        ]

        idx = 6
        for region in regions:
            region_col = create_sum_column(
                yigma_statement,
                main_title,
                region,
                f"1.1.{idx}",
            )

            create_sum_column(yigma_statement, region_col, "Reja", f"1.1.{idx}.1")
            create_sum_column(yigma_statement, region_col, "Amalda", f"1.1.{idx}.2")
            create_sum_column(yigma_statement, region_col, "Foizi", f"1.1.{idx}.3")

            idx += 1

        self.stdout.write(
            self.style.SUCCESS("✅ Yig'ma statement uchun SumColumn lar yaratildi!")
        )
