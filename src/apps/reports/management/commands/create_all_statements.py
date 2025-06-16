import random
from django.core.management import BaseCommand

from apps.utils.services import RegionChoices
from apps.reports.models import Statement


class Command(BaseCommand):
    def handle(self, *args, **options):
        Statement.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Organizations have been created !."))