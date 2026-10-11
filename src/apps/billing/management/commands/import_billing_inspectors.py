"""
Eski billing (billing-urmon.uz) "Inspektor" foydalanuvchilarini stat'ga ko'chirish.

Kirish: billing serverda eksport qilingan JSON (ro'yxat), har yozuv:
  username, email, first_name, sur_name, mid_name, phone, status (1 New, 2 Active, 3 Deleted),
  password (Django hash — o'zgarishsiz ko'chiriladi, foydalanuvchi o'sha paroli bilan kiradi),
  departments [{name, inn}], xojaliklar [{name, department}]

    python manage.py import_billing_inspectors --file /app/media/inspektorlar.json [--dry-run] [--update]
        [--email-domain billing-urmon.uz]

- Stat'da login email bilan: billing'da email bo'lsa shu, bo'lmasa `<username>@<domen>`.
- Xo'jaliklar: department nomi/INN va xojaliklar nomi bo'yicha stat `Xojalik` dan topiladi
  (nom solishtirishda bo'sh joy/apostrof farqlari e'tiborga olinmaydi).
- Mavjud billing foydalanuvchisi: `--update` bo'lsa ism/parol/xo'jaliklar yangilanadi, aks holda o'tkaziladi.
  Boshqa roldagi mavjud email har doim o'tkazib yuboriladi.
"""
import json
import re

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.billing.models import BillingUserAccess, Xojalik
from apps.users.models import CustomUser

BILLING_ROLES = {CustomUser.Role.BILLING_USER, CustomUser.Role.BILLING_SUPER}


def _norm(name: str) -> str:
    s = (name or "").strip().lower()
    s = s.replace("ʻ", "'").replace("ʼ", "'").replace("’", "'").replace("‘", "'").replace("`", "'")
    return re.sub(r"\s+", " ", s)


class Command(BaseCommand):
    help = "billing-urmon.uz inspektorlarini billing_user sifatida ko'chiradi (parol hash'i bilan)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Eksport JSON fayli")
        parser.add_argument("--email-domain", default="billing-urmon.uz",
                            help="Email'siz foydalanuvchilar uchun: <username>@<domen>")
        parser.add_argument("--dry-run", action="store_true", help="Faqat hisobot, yozmaydi")
        parser.add_argument("--update", action="store_true",
                            help="Mavjud billing foydalanuvchilarining ism, parol va xo'jaliklarini yangilash")
        parser.add_argument("--include-deleted", action="store_true", help="status=3 (Deleted) ham ko'chirilsin")

    # ---------- yordamchilar ----------
    def _load(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise CommandError(f"JSON o'qilmadi: {e}")
        if not isinstance(data, list):
            raise CommandError("JSON ro'yxat bo'lishi kerak")
        return data

    def _xojalik_index(self):
        by_name, by_inn = {}, {}
        for x in Xojalik.objects.all():
            by_name[_norm(x.name)] = x
            if x.inn:
                by_inn[x.inn.strip()] = x
        return by_name, by_inn

    def _resolve_email(self, rec, domain):
        email = (rec.get("email") or "").strip().lower()
        if email:
            try:
                validate_email(email)
                return email
            except ValidationError:
                pass
        username = (rec.get("username") or "").strip().lower()
        if not username:
            return None
        if "@" in username:
            try:
                validate_email(username)
                return username
            except ValidationError:
                pass
        local = re.sub(r"[^a-z0-9._-]", "_", username).strip("._-") or f"user{rec.get('id', '')}"
        return f"{local}@{domain}"

    def _match_xojaliklar(self, rec, by_name, by_inn):
        found, missing = {}, []
        candidates = []
        for d in rec.get("departments") or []:
            candidates.append((d.get("name"), d.get("inn")))
        for x in rec.get("xojaliklar") or []:
            candidates.append((x.get("name"), None))
            if x.get("department"):
                candidates.append((x.get("department"), None))
        for name, inn in candidates:
            x = None
            if inn and str(inn).strip() in by_inn:
                x = by_inn[str(inn).strip()]
            elif name and _norm(name) in by_name:
                x = by_name[_norm(name)]
            if x is not None:
                found[x.id] = x
            elif name and name not in missing:
                missing.append(name)
        # departments bo'yicha topilgan bo'lsa, xojaliklar nomlari "missing" sifatida ko'rsatilmaydi
        return list(found.values()), (missing if not found else [m for m in missing if m not in {
            x.get("name") for x in rec.get("xojaliklar") or []}])

    # ---------- asosiy ----------
    def handle(self, *args, **options):
        records = self._load(options["file"])
        domain = options["email_domain"].strip().lower()
        dry = options["dry_run"]
        update = options["update"]

        by_name, by_inn = self._xojalik_index()
        group = None if dry else Group.objects.get_or_create(name=CustomUser.Role.BILLING_USER.value)[0]

        created = updated = existed = skipped = 0
        mapping, unmatched, no_xojalik = [], [], []

        if dry:
            self.stdout.write(self.style.WARNING("DRY RUN — bazaga yozilmaydi"))

        for rec in records:
            username = (rec.get("username") or "").strip()
            status = rec.get("status")
            if status == 3 and not options["include_deleted"]:
                skipped += 1
                self.stdout.write(f"  o'tkazib yuborildi (o'chirilgan): {username}")
                continue

            email = self._resolve_email(rec, domain)
            if not email:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"  o'tkazib yuborildi (username ham email ham yo'q): id={rec.get('id')}"))
                continue

            xojaliklar, missing = self._match_xojaliklar(rec, by_name, by_inn)
            for m in missing:
                unmatched.append((username, m))
            if not xojaliklar:
                no_xojalik.append(username)

            first_name = (rec.get("first_name") or "").strip() or username
            last_name = (rec.get("sur_name") or "").strip() or "-"
            father_name = (rec.get("mid_name") or "").strip()
            phone = (rec.get("phone") or "").strip() or None
            password_hash = rec.get("password") or ""

            existing = CustomUser.objects.filter(email__iexact=email).first()
            if existing is not None and existing.role not in BILLING_ROLES:
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"  o'tkazib yuborildi: {username} -> {email} boshqa roldagi ({existing.role}) foydalanuvchiniki"))
                continue

            mapping.append((username, email))
            if existing is not None:
                existed += 1
                if not update:
                    continue
                if not dry:
                    self._apply(existing, username, first_name, last_name, father_name, phone, password_hash, xojaliklar, group)
                updated += 1
                continue

            created += 1
            if dry:
                continue
            with transaction.atomic():
                user = CustomUser(
                    email=email, first_name=first_name, last_name=last_name,
                    role=CustomUser.Role.BILLING_USER, is_active=True,
                )
                self._apply(user, username, first_name, last_name, father_name, phone, password_hash, xojaliklar, group)

        # ---------- hisobot ----------
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Natija: yaratildi: {created}, mavjud: {existed} (yangilandi: {updated}), o'tkazib yuborildi: {skipped}"))
        self.stdout.write("Login (billing username -> stat email; ikkalasi bilan ham kirish mumkin):")
        for username, email in mapping:
            self.stdout.write(f"  {username} -> {email}")
        if no_xojalik:
            self.stdout.write(self.style.WARNING(
                f"Xo'jaliksiz ({len(no_xojalik)}) — /billing-admin/ da biriktiring: {', '.join(no_xojalik)}"))
        if unmatched:
            self.stdout.write(self.style.WARNING("Topilmagan xo'jaliklar:"))
            for username, name in unmatched:
                self.stdout.write(f"  {username}: {name}")

    def _apply(self, user, username, first_name, last_name, father_name, phone, password_hash, xojaliklar, group):
        user.first_name = first_name
        user.last_name = last_name
        user.father_name = father_name
        # Eski login saqlanadi — stat'ga shu login bilan ham kiradi (EmailBackend)
        if username:
            clash = CustomUser.objects.filter(username__iexact=username).exclude(pk=user.pk).first()
            if clash is None:
                user.username = username.lower()
            else:
                self.stdout.write(self.style.WARNING(
                    f"  login '{username}' boshqa foydalanuvchida ({clash.email}) — {user.email} faqat email bilan kiradi"))
        if phone:
            try:
                user.phone_number = phone
                user.clean_fields(exclude=[f.name for f in user._meta.fields if f.name != "phone_number"])
            except ValidationError:
                user.phone_number = ""  # formati stat validatoriga to'g'ri kelmasa
        elif not user.phone_number:
            user.phone_number = ""
        if password_hash and not password_hash.startswith("!"):
            user.password = password_hash
        elif not user.password:
            user.set_unusable_password()
        user.save()
        if group is not None:
            user.groups.add(group)
        access, _ = BillingUserAccess.objects.get_or_create(user=user)
        access.xojaliklar.set(xojaliklar)
