from django.core.management.base import BaseCommand
from apps.reports.models import Statement, Plant
from modeltranslation.utils import auto_populate


class Command(BaseCommand):
    help = "Creates plants for 'Shakl 8-O'X' statement (safe & idempotent)"

    def handle(self, *args, **kwargs):
        with auto_populate('ru'):
            # 1. Statementni topamiz
            statement = Statement.objects.filter(
                name_uz__icontains="Shakl 8-O'X"
            ).first()

            if not statement:
                self.stderr.write(self.style.ERROR(
                    "❌ Statement not found: Shakl 8-O'X"
                ))
                return

            # 2. Parent plant (kategoriya)
            parent_name = "Shakl 8-O'X"
            parent, _ = Plant.objects.get_or_create(
                name_uz=parent_name,
                parent=None,
                defaults={
                    "name_ru": parent_name,
                    "statement": statement,
                }
            )

            # Agar oldin yaratilgan bo‘lsa ham majburan bog‘laymiz
            parent.statement = statement
            parent.save(update_fields=["statement"])

            # 3. Plantlar (UZ, RU)
            plants = [
                ("archa", "можжевельник"),
                ("tuya", "туя"),
                ("qrim qarag‘ayi", "крымская сосна"),
                ("eldor qarag‘ay", "сосна эльдарская"),
                ("kiparis", "кипарис"),
                ("terak", "тополь"),
                ("qayrogoch", "вяз"),
                ("yasen", "ясень"),
                ("tol", "ива"),
                ("chinor", "чинар"),
                ("majnuntol", "плакучая ива"),
                ("sofora", "софора"),
                ("pavloniya", "павловния"),
                ("yong‘oq", "грецкий орех"),
                ("o‘rik", "абрикос"),
                ("olcha", "вишня"),
                ("gilos", "черешня"),
                ("qizil do‘lana", "боярышник красный"),
                ("tut", "шелковица"),
                ("jiyda", "лох"),
                ("uzum", "виноград"),
                ("bag‘ryannik", "багрянник"),
                ("dub", "дуб"),
                ("kashtan", "каштан"),
                ("katalpa", "катальпа"),
                ("akatsiya ipak", "акация шелковая"),
                ("aylant", "айлант"),
                ("klyon", "клён"),
                ("na'matak", "шиповник"),
                ("samshit", "самшит"),
                ("Suriya sireni", "гибискус сирийский"),
                ("Hind sireni", "сирень индийская"),
                ("atirgul", "роза"),
                ("lavanda", "лаванда"),
                ("xrizantema", "хризантема"),
            ]

            created_count = 0
            updated_count = 0

            # 4. Child plantlarni yaratamiz / to‘g‘rilaymiz
            for uz_name, ru_name in plants:
                obj, created = Plant.objects.get_or_create(
                    name_uz=uz_name,
                    parent=parent,
                    defaults={
                        "name_ru": ru_name,
                        "statement": statement,
                    }
                )

                # Agar oldin bo‘lsa ham majburan to‘g‘rilaymiz
                changed = False
                if obj.statement_id != statement.id:
                    obj.statement = statement
                    changed = True

                if obj.parent_id != parent.id:
                    obj.parent = parent
                    changed = True

                if obj.name_ru != ru_name:
                    obj.name_ru = ru_name
                    changed = True

                if changed:
                    obj.save()
                    updated_count += 1

                if created:
                    created_count += 1

            self.stdout.write(self.style.SUCCESS(
                f"✅ Done. Created: {created_count}, Updated: {updated_count}"
            ))
