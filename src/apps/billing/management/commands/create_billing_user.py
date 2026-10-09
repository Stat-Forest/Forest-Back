"""
Ijara billing foydalanuvchisini yaratish:

    python manage.py create_billing_user --email e@x.uz --password '...' \
        --first-name Ism --last-name Familiya [--role billing_user|billing_super] \
        [--xojalik "Xo'jalik nomi yoki INN" ...]

`billing_user` faqat `--xojalik` bilan biriktirilgan xo'jaliklar doirasida ishlaydi
(`--xojalik` bir necha marta berilishi mumkin); `billing_super` — barcha xo'jaliklar.
"""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.billing.models import BillingUserAccess, Xojalik
from apps.users.models import CustomUser

ROLE_CHOICES = (CustomUser.Role.BILLING_USER.value, CustomUser.Role.BILLING_SUPER.value)


class Command(BaseCommand):
    help = "Ijara billing foydalanuvchisini (billing_user yoki billing_super) yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--first-name", required=True)
        parser.add_argument("--last-name", required=True)
        parser.add_argument("--role", choices=ROLE_CHOICES, default=CustomUser.Role.BILLING_USER.value)
        parser.add_argument(
            "--xojalik", action="append", default=[], metavar="NOM_YOKI_INN",
            help="Biriktiriladigan xo'jalik nomi yoki INN (takrorlanadi)",
        )

    @staticmethod
    def _resolve_xojaliklar(values):
        found, missing = [], []
        for raw in values:
            value = (raw or "").strip()
            if not value:
                continue
            matches = list(Xojalik.objects.filter(Q(inn=value) | Q(name__iexact=value))[:2])
            if len(matches) != 1:
                missing.append(value)
            else:
                found.append(matches[0])
        if missing:
            raise CommandError(f"Xo'jalik topilmadi yoki aniq emas: {', '.join(missing)}")
        return found

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        role = options["role"]
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise CommandError(f"'{email}' elektron pochtali foydalanuvchi allaqachon mavjud.")
        xojaliklar = self._resolve_xojaliklar(options["xojalik"])
        if role == CustomUser.Role.BILLING_SUPER and xojaliklar:
            self.stdout.write(self.style.WARNING("billing_super barcha xo'jaliklarni ko'radi — --xojalik e'tiborga olinmaydi."))
            xojaliklar = []
        if role == CustomUser.Role.BILLING_USER and not xojaliklar:
            self.stdout.write(self.style.WARNING(
                "Xo'jalik biriktirilmadi — foydalanuvchi hech narsani ko'rmaydi (keyin /billing-admin/ da biriktiring)."
            ))

        with transaction.atomic():
            user = CustomUser.objects.create_user(
                email=email,
                password=options["password"],
                first_name=options["first_name"],
                last_name=options["last_name"],
                role=role,
            )
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.set([group])
            access, _ = BillingUserAccess.objects.get_or_create(user=user)
            access.xojaliklar.set(xojaliklar)

        names = ", ".join(x.name for x in xojaliklar) or "—"
        self.stdout.write(self.style.SUCCESS(f"Billing foydalanuvchisi yaratildi: {email} ({role}); xo'jaliklar: {names}"))
