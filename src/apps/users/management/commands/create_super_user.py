from django.core.management.base import BaseCommand
from getpass import getpass

from apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Creates a superuser with minimal required fields (email, first_name, last_name, password)"

    def handle(self, *args, **options):
        email = "forest@gmail.com"
        password = "1"
        first_name = "Admin"
        last_name = "User"

        if CustomUser.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f"Superuser with email '{email}' already exists."))
        else:
            CustomUser.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{email}' created successfully."))