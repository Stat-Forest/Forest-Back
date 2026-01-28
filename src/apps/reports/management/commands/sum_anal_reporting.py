from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = "Create Yashil Makon Yigma report columns"

    def handle(self, *args, **options):

        def create_statement(parent, name_uz, name_ru, period=None):
            obj, _ = Statement.objects.get_or_create(
                parent=parent,
                name=name_uz,
                defaults={
                    "name_uz": name_uz,
                    "name_ru": name_ru,
                    "period": period,
                }
            )
            return obj

        def create_column(statement, parent, title_uz, title_ru, ordering, is_user_input=True):
            obj, _ = StatementColumn.objects.get_or_create(
                statement=statement,
                parent=parent,
                ordering=ordering,
                defaults={
                    "title": title_uz,
                    "title_uz": title_uz,
                    "title_ru": title_ru,
                    "is_user_input": is_user_input,
                }
            )
            return obj

        # 1️⃣ Asosiy statement
        base_statement = Statement.objects.get(
            name_uz="Axborot-tahlil, ijro intizomi"
        )

        # 2️⃣ Yig'ma statement
        yigma_statement = create_statement(
            parent=base_statement,
            name_uz="Yig'ma",
            name_ru="Сводный",
        )

        # 🔹 YANGI: Yig'ma ilovasi
        yigma_ilovasi = create_column(
            yigma_statement,
            parent=None,
            title_uz="Yig'ma ilovasi",
            title_ru="Сводное приложение",
            ordering="1"
        )

        # 3️⃣ Asosiy sarlavha (endi parent = yig'ma ilovasi)
        main_title = create_column(
            yigma_statement,
            yigma_ilovasi,
            "O‘rmon agentligiga yuklatilgan muhim vazifalar ijrosi to‘g‘risida ma’lumoti",
            "Информация о выполнении важных задач, возложенных на Агентство лесного хозяйства",
            "1.1"
        )

        # 4️⃣ CHAP TOMON USTUNLAR
        create_column(yigma_statement, main_title,
                      "Maqsadli ko‘rsatkich nomi",
                      "Наименование целевого показателя",
                      "1.1.1")

        create_column(yigma_statement, main_title,
                      "O‘lchov birligi",
                      "Единица измерения",
                      "1.1.2")

        create_column(yigma_statement, main_title,
                      "Yillik reja",
                      "План на год",
                      "1.1.3")

        create_column(yigma_statement, main_title,
                      "Amalda",
                      "Фактически",
                      "1.1.4")

        bajarilishi = create_column(
            yigma_statement,
            main_title,
            "Bajarilishi",
            "Исполнение",
            "1.1.5",
        )

        create_column(
            yigma_statement,
            bajarilishi,
            "Foizi",
            "Процент",
            "1.1.5.1",
        )

        create_column(
            yigma_statement,
            bajarilishi,
            "Farqi (+;-)",
            "Отклонение (+;-)",
            "1.1.5.2",
        )

        # 5️⃣ HUDUDLAR
        regions = [
            ("Qoraqalpog‘iston Respublikasi", "Республика Каракалпакстан"),
            ("Andijon", "Андижан"),
            ("Buxoro", "Бухара"),
            ("Jizzax", "Джизак"),
            ("Qashqadaryo", "Кашкадарья"),
            ("Navoiy", "Навои"),
            ("Namangan", "Наманган"),
            ("Samarqand", "Самарканд"),
            ("Surxondaryo", "Сурхандарья"),
            ("Sirdaryo", "Сырдарья"),
            ("Toshkent viloyati", "Ташкентская область"),
            ("Farg‘ona", "Фергана"),
            ("Xorazm", "Хорезм"),
        ]

        idx = 6
        for uz, ru in regions:
            region_col = create_column(
                yigma_statement,
                main_title,
                uz,
                ru,
                f"1.1.{idx}"
            )

            create_column(yigma_statement, region_col, "Reja", "План", f"1.1.{idx}.1")
            create_column(yigma_statement, region_col, "Amalda", "Фактически", f"1.1.{idx}.2")
            create_column(
                yigma_statement,
                region_col,
                "Foizi",
                "Процент",
                f"1.1.{idx}.3",
            )

            idx += 1

        self.stdout.write(
            self.style.SUCCESS("✅ Yig'ma ilovasi bilan hisoboti ustunlari yaratildi!")
        )
