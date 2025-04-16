from django.core.management.base import BaseCommand

from apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Creates a superuser"

    def handle(self, *args, **options):
        email = input("Enter email: ").strip()
        first_name = input("Enter first name: ").strip()
        password = input("Enter password: ").strip()

        if not email or not first_name or not password:
            self.stdout.write(self.style.ERROR("All fields are required."))
            return self.handle()

        try:
            CustomUser.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name
            )
            self.stdout.write(self.style.SUCCESS("SuperUser created successfully!!!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
