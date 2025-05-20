from django.core.management.base import BaseCommand
from getpass import getpass

from apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Creates a superuser with minimal required fields (email, first_name, last_name, password)"

    def handle(self, *args, **options):
        try:
            email = input("Email: ").strip()
            first_name = input("First name: ").strip()
            last_name = input("Last name: ").strip()
            password = getpass("Password: ")

            user = CustomUser.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            self.stdout.write(self.style.SUCCESS(f"Superuser '{user.email}' created successfully."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
