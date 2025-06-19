from django.core.management.base import BaseCommand
from getpass import getpass

from apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Creates a superuser with 'tashkilot_hodimi' role (email, first_name, last_name, password)"

    def handle(self, *args, **options):
        try:
            email = input("Email: ").strip()
            first_name = input("First name: ").strip()
            last_name = input("Last name: ").strip()
            password = getpass("Password: ")

            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=CustomUser.Role.TASHKILOT_HODIMI
            )

            self.stdout.write(self.style.SUCCESS(
                f"Tashkilot hodimi superuser '{user.email}' created successfully."
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
