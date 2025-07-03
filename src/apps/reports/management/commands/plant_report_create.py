from django.db.models import Q
from django.core.management.base import BaseCommand

from apps.reports.models import StatementColumn, Plant, ColumnPlant


class Command(BaseCommand):
    help = "Assign all child plants to 'Ko‘chat' and 'Nihol' statement columns"

    def handle(self, *args, **options):

        plant_columns = StatementColumn.objects.filter(
            Q(title_uz__iexact="Ko‘chat") | Q(title_uz__iexact="Nihol")
        )

        plants = Plant.objects.exclude(parent=None)

        count = 0
        for column in plant_columns:
            for plant in plants:
                ColumnPlant.objects.get_or_create(
                    column=column,
                    plant=plant
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {count} ColumnPlant records created."))
