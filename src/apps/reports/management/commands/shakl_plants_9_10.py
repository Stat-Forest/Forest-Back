from django.core.management.base import BaseCommand
from apps.reports.models import Statement, Plant
from modeltranslation.utils import auto_populate


class Command(BaseCommand):
    help = "Creates year-based plants for Shakl 9-O‘X and Shakl 10-O‘X"

    YEARS = [
        ("2012 va avvalgi yillar", "2012 и предыдущие годы"),
        ("2013 yil", "2013 год"),
        ("2014 yil", "2014 год"),
        ("2015 yil", "2015 год"),
        ("2016 yil", "2016 год"),
        ("2017 yil", "2017 год"),
        ("2018 yil", "2018 год"),
        ("2019 yil", "2019 год"),
        ("2020 yil", "2020 год"),
        ("2021 yil", "2021 год"),
        ("2022 yil", "2022 год"),
        ("2023 yil", "2023 год"),
        ("2024 yil", "2024 год"),
        ("2025 yil", "2025 год"),
    ]

    def handle(self, *args, **kwargs):
        with auto_populate('ru'):
            for name_uz in ["Shakl 9-O‘X", "Shakl 10-O‘X"]:
                statement = Statement.objects.filter(name_uz__icontains=name_uz).first()
                if not statement:
                    self.stderr.write(self.style.ERROR(f"❌ Statement not found: {name_uz}"))
                    continue

                # Create parent plant
                parent_uz = "O‘rmon osti boyliklaridan foydalanilgan yil"
                parent_ru = "Год использования недревесных ресурсов"

                parent, _ = Plant.objects.get_or_create(
                    name_uz=parent_uz,
                    parent=None,
                    statement=statement,
                    defaults={"name_ru": parent_ru},
                )

                changed = False
                if parent.statement_id != statement.id:
                    parent.statement = statement
                    changed = True
                if changed:
                    parent.save(update_fields=["statement"])

                created, updated = 0, 0

                for uz, ru in self.YEARS:
                    obj, is_created = Plant.objects.get_or_create(
                        name_uz=uz,
                        parent=parent,
                        statement=statement,  # <-- fix: statement bo‘yicha ham ajratilsin
                        defaults={"name_ru": ru},
                    )

                    need_save = False
                    if obj.name_ru != ru:
                        obj.name_ru = ru
                        need_save = True
                    if need_save:
                        obj.save()
                        updated += 1
                    if is_created:
                        created += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {name_uz}: {created} ta yangi, {updated} ta yangilandi."
                    )
                )
