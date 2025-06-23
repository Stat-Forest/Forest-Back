from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


class Command(BaseCommand):
    help = "Run multiple management commands one after another"

    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.WARNING("Running: create_employee_report and create_employee_analysis"))
            call_command('create_employee_report')
            call_command('create_employee_analysis')

            self.stdout.write(self.style.WARNING("Running: income_and_fund"))
            call_command('income_and_fund')

            self.stdout.write(self.style.WARNING("Running: create_management_land"))
            call_command('create_management_land')

            self.stdout.write(self.style.SUCCESS("All commands executed successfully."))

        except CommandError as e:
            self.stderr.write(self.style.ERROR(f"Error occurred: {e}"))

