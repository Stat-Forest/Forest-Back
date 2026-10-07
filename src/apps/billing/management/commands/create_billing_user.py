"""`billing_user` rolli foydalanuvchi yaratish: --email --password --first-name --last-name."""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Ijara billing foydalanuvchisini (role=billing_user) yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--first-name", required=True)
        parser.add_argument("--last-name", required=True)

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise CommandError(f"'{email}' elektron pochtali foydalanuvchi allaqachon mavjud.")
        user = CustomUser.objects.create_user(
            email=email,
            password=options["password"],
            first_name=options["first_name"],
            last_name=options["last_name"],
            role=CustomUser.Role.BILLING_USER,
        )
        group, _ = Group.objects.get_or_create(name=CustomUser.Role.BILLING_USER.value)
        user.groups.set([group])
        self.stdout.write(self.style.SUCCESS(f"Billing foydalanuvchisi yaratildi: {email}"))
