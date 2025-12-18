from django.core.management.base import BaseCommand
from apps.reports.models import Statement, Plant
from modeltranslation.utils import auto_populate


class Command(BaseCommand):
    help = "Creates natural regeneration measures (2.1–2.7) for 'Shakl 11-O‘X' (safe & idempotent)"

    def handle(self, *args, **kwargs):
        with auto_populate('ru'):

            # 1. Statementni topamiz
            statement = Statement.objects.filter(
                name_uz__icontains="Shakl 11-O‘X"
            ).first()

            if not statement:
                self.stderr.write(
                    self.style.ERROR("❌ Statement not found: Shakl 11-O‘X")
                )
                return

            # 2. ASOSIY PARENT
            parent_uz = "Tabiiy tiklanishga ko‘maklashildi"
            parent_ru = "Оказано содействие естественному возобновлению"

            parent, _ = Plant.objects.get_or_create(
                name_uz=parent_uz,
                parent=None,
                defaults={
                    "name_ru": parent_ru,
                    "statement": statement,
                }
            )

            # majburan bog‘lab qo‘yamiz
            changed = False
            if parent.statement_id != statement.id:
                parent.statement = statement
                changed = True

            if changed:
                parent.save(update_fields=["statement"])

            # 3. 2.1–2.7 CHILD PLANTLAR
            children = [
                (
                    "Kesilgan maydonlarda daraxt to‘nkalarini ko‘kartirishni ta’minlash",
                    "Обеспечение отрастания пней деревьев на вырубках",
                ),
                (
                    "Sug‘orish (yoppasiga to‘qaylarda ...)",
                    "Орошение (в сплошных тугайных насаждениях и др.)",
                ),
                (
                    "Sun’iy urug‘ sepish (shamol kam va urug‘ tarqalishi qiyin hududda)",
                    "Искусственный посев семян (в районах со слабым ветром и трудным распространением семян)",
                ),
                (
                    "Mexanik usulda yerga ishlov berish",
                    "Механическая обработка почвы",
                ),
                (
                    "Kimyoviy usulda yerga ishlov berish",
                    "Химическая обработка почвы",
                ),
                (
                    "Hududni panjara yoki boshqa unsurlar bilan o‘rash",
                    "Ограждение территории заборами или другими элементами",
                ),
                (
                    "Boshqa yo‘llar bilan daraxtni tabiiy ko‘paytirish (aniq ko‘rsatish lozim)",
                    "Другие способы естественного возобновления деревьев (указать конкретно)",
                ),
            ]

            created = 0
            updated = 0

            for uz_name, ru_name in children:
                obj, is_created = Plant.objects.get_or_create(
                    name_uz=uz_name,
                    parent=parent,
                    defaults={
                        "name_ru": ru_name,
                        "statement": statement,
                    }
                )

                need_save = False

                if obj.statement_id != statement.id:
                    obj.statement = statement
                    need_save = True

                if obj.parent_id != parent.id:
                    obj.parent = parent
                    need_save = True

                if obj.name_ru != ru_name:
                    obj.name_ru = ru_name
                    need_save = True

                if need_save:
                    obj.save()
                    updated += 1

                if is_created:
                    created += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Shakl 11-O‘X (2.1–2.7) done. Created: {created}, Updated: {updated}"
                )
            )
