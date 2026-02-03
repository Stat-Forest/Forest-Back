import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run all forest establishment commands sequentially"

    def handle(self, *args, **options):
        commands = [
            "python manage.py forest_establishment",
            "python manage.py second_forest_establishment",
            "python manage.py third_forest_establishment",
            "python manage.py fourth_forest_establishment",
            "python manage.py plant_create_nihol",
            "python manage.py plant_create_urug",
            "python manage.py forest_protect",
            "python manage.py forest_additional",
            "python manage.py second_forest_additional",
            "python manage.py third_forest_additional",
            "python manage.py shakl_reports",
            "python manage.py shakl_plants_8",
            "python manage.py shakl_plants_9_10",
            "python manage.py shakl_plants_11",
        ]

        for cmd in commands:
            self.stdout.write(self.style.WARNING(f"⏳ Running: {cmd}"))
            exit_code = os.system(cmd)
            if exit_code == 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Successfully finished: {cmd}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Failed: {cmd}"))
                break
