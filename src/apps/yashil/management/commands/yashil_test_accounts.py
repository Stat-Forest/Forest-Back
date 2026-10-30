"""
Ishchi serverda sinov hisoblari — mavjud (haqiqiy) mahalla va unga biriktirilgan tashkilotlarga ulanadi.
Soxta mahalla, tashkilot yoki katalog yaratilmaydi (buning uchun `yashil_seed_demo` — faqat lokal).

    python manage.py yashil_test_accounts --list                 # mahallalar va biriktirishlar
    python manage.py yashil_test_accounts --mahalla <kod>        # 4 kabinet: mahalla, uyushma, xo'jalik, kuzatuvchi
    python manage.py yashil_test_accounts --mahalla <kod> --pinfl   # imzo uchun JSHSHIR (E-IMZO kalitingizniki)
    python manage.py yashil_test_accounts --set-password         # parolni almashtirish
    python manage.py yashil_test_accounts --disable              # hammasini o'chirish (nofaol)

Hisoblar: ym-test-<kabinet>@<domen>. Parol va JSHSHIR terminalda so'raladi — buyruq qatorida,
tarixda va chiqishda ko'rinmaydi. Rollar faqat modul URL'lariga ruxsat beradi (ym_*):
yetkazib beruvchi hisobi tashkilotning hisobotlariga kirmaydi.
"""
import re
from datetime import date
from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.yashil.models import Mahalla, MahallaUnionRoute, SupplierAssignment, YashilMembership

PREFIX = "ym-test-"
T = YashilMembership.MemberType
ROLES = {"mahalla": "ym_mahalla", "union": "ym_union", "supplier": "ym_dm", "observer": "ym_observer"}
NAMES = {"mahalla": "Mahalla", "union": "Uyushma", "supplier": "Xo'jalik", "observer": "Kuzatuvchi"}
SIGNERS = ("mahalla", "supplier")


def _active(qs, on):
    return qs.filter(valid_from__lte=on).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=on)).order_by("-valid_from")


class Command(BaseCommand):
    help = "Yashil mahalla: mavjud mahallaga ulangan sinov hisoblari (ishchi server uchun)"

    def add_arguments(self, parser):
        parser.add_argument("--list", action="store_true", help="Mahallalar, xo'jalik va uyushma biriktirishlari")
        parser.add_argument("--mahalla", default="", help="Mahalla kodi (source_code)")
        parser.add_argument("--domain", default="stat-urmon.uz", help="Email domeni")
        parser.add_argument("--pinfl", action="store_true", help="Imzolovchi kabinetlarga JSHSHIR (so'raladi)")
        parser.add_argument("--set-password", action="store_true", help="Mavjud hisoblar parolini almashtirish")
        parser.add_argument("--disable", action="store_true", help="Barcha sinov hisoblarini nofaol qilish")

    def handle(self, *args, **opts):
        if opts["list"]:
            return self._list()
        if opts["disable"]:
            return self._disable()
        if opts["mahalla"]:
            return self._create(opts)
        if opts["set_password"]:
            return self._set_password()
        raise CommandError("--list, --mahalla <kod>, --set-password yoki --disable kerak")

    # ------------------------------------------------------------------ ro'yxat
    def _list(self):
        today = date.today()
        mahallas = Mahalla.objects.select_related("region", "district").order_by("region__name", "district__name", "name")
        if not mahallas.exists():
            self.stdout.write("Mahalla yo'q — avval «Ma'muriyat → Mahallalar» orqali qo'shing yoki import qiling.")
            return
        for m in mahallas[:200]:
            a = _active(SupplierAssignment.objects.filter(mahalla=m), today).select_related("organization").first()
            r = _active(MahallaUnionRoute.objects.filter(mahalla=m), today).select_related("union_unit").first()
            self.stdout.write(f"{m.source_code} | {m.name} | {m.district.name} | "
                              f"xo'jalik: {a.organization.name if a else '—'} | uyushma: {r.union_unit.name if r else '—'}")
        self.stdout.write(f"Jami: {mahallas.count()}")
        self._show_existing()

    def _show_existing(self):
        users = get_user_model().objects.filter(email__startswith=PREFIX).order_by("email")
        for u in users:
            cabs = ", ".join(f"{ms.member_type}: {ms.cabinet_name}" for ms in u.yashil_memberships.all())
            self.stdout.write(f"  {u.email} | {'faol' if u.is_active else 'nofaol'} | {cabs or '—'}")

    # ------------------------------------------------------------------ yaratish
    def _create(self, opts):
        today = date.today()
        mahalla = Mahalla.objects.select_related("region").filter(source_code=opts["mahalla"]).first()
        if mahalla is None:
            raise CommandError(f"Mahalla topilmadi: {opts['mahalla']} (ro'yxat: --list)")
        a = _active(SupplierAssignment.objects.filter(mahalla=mahalla), today).first()
        r = _active(MahallaUnionRoute.objects.filter(mahalla=mahalla), today).first()
        targets = {
            "mahalla": {"member_type": T.MAHALLA, "mahalla": mahalla, "can_sign": True},
            "union": {"member_type": T.UNION, "union_unit_id": r.union_unit_id, "can_sign": False} if r else None,
            "supplier": {"member_type": T.SUPPLIER, "organization_id": a.organization_id, "can_sign": True} if a else None,
            "observer": {"member_type": T.OBSERVER, "can_prepare": False, "can_sign": False,
                         "observer_scope": {"regions": [mahalla.region.code]}},
        }
        for kind in ("union", "supplier"):
            if targets[kind] is None:
                self.stdout.write(self.style.WARNING(f"{kind}: mahallaga biriktirilmagan — o'tkazib yuborildi"))
        targets = {k: v for k, v in targets.items() if v}

        User = get_user_model()
        emails = {k: f"{PREFIX}{k}@{opts['domain']}" for k in targets}
        existing = set(User.objects.filter(email__in=emails.values()).values_list("email", flat=True))
        password = self._ask_password() if opts["set_password"] or set(emails.values()) - existing else None
        pinfl = self._ask_pinfl() if opts["pinfl"] else None

        with transaction.atomic():
            for kind, fields in targets.items():
                user = User.objects.filter(email=emails[kind]).first()
                if user is None:
                    user = User.objects.create_user(email=emails[kind], password=password, first_name=NAMES[kind],
                                                    last_name="Sinov", role=ROLES[kind])
                else:
                    user.role, user.is_active = ROLES[kind], True
                    if password:
                        user.set_password(password)
                if pinfl and kind in SIGNERS:
                    user.pinfl = pinfl
                user.save()
                self._membership(user, fields, today)
        self.stdout.write(self.style.SUCCESS(f"Mahalla: {mahalla.source_code} — {mahalla.name}"))
        self._show_existing()

    def _membership(self, user, fields, today):
        fields = dict(fields)
        member_type = fields.pop("member_type")
        fields.setdefault("can_prepare", True)
        # bitta sinov hisobida bitta kabinet: boshqa mahalla tanlansa eskisi almashtiriladi
        user.yashil_memberships.exclude(member_type=member_type).update(is_active=False)
        ms = user.yashil_memberships.filter(member_type=member_type).first() or YashilMembership(user=user, member_type=member_type)
        for name in ("mahalla", "union_unit_id", "organization_id"):
            setattr(ms, name, None)
        for name, value in fields.items():
            setattr(ms, name, value)
        ms.is_active, ms.valid_from, ms.valid_to = True, today, None
        ms.position_title = "Sinov hisobi"
        try:
            ms.save()
        except ValidationError as e:
            raise CommandError(f"{user.email}: {e}") from e

    # ------------------------------------------------------------------ boshqalar
    def _set_password(self):
        users = list(get_user_model().objects.filter(email__startswith=PREFIX))
        if not users:
            raise CommandError("Sinov hisoblari yo'q")
        password = self._ask_password()
        for u in users:
            u.set_password(password)
            u.save(update_fields=["password"])
        self.stdout.write(self.style.SUCCESS(f"Parol almashtirildi: {len(users)} ta hisob"))

    def _disable(self):
        users = get_user_model().objects.filter(email__startswith=PREFIX)
        n = users.update(is_active=False)
        YashilMembership.objects.filter(user__email__startswith=PREFIX).update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f"Nofaol qilindi: {n} ta hisob"))

    def _ask_password(self) -> str:
        first = getpass("Sinov hisoblari uchun parol: ")
        if getpass("Parolni qayta kiriting: ") != first:
            raise CommandError("Parollar mos emas")
        try:
            validate_password(first)
        except ValidationError as e:
            raise CommandError("Parol talablarga mos emas: " + "; ".join(e.messages)) from e
        return first

    def _ask_pinfl(self) -> str:
        value = getpass("Imzo uchun JSHSHIR (E-IMZO kalitingizdagi 14 raqam): ").strip()
        if not re.fullmatch(r"\d{14}", value):
            raise CommandError("JSHSHIR 14 ta raqam bo'lishi kerak")
        return value
