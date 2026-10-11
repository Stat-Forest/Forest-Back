"""
Eski billing (billing-urmon.uz) shartnomalarini stat'ga to'liq ko'chirish.

Kirish: `docs/billing-shartnoma-eksport.py` bilan olingan `contracts.json`
(ma'lumotnoma, ijarachilar, shartnomalar: faoliyat/yer/imtiyoz turlari, harakatlar,
yillik summalar, fayllar ro'yxati, tarix) va media papkasi (fayllar).

    python manage.py import_billing_contracts --file /app/media/legacy_billing/contracts.json \\
        --media-root /app/media/legacy_billing/media [--dry-run]

Moslashtirish:
- Viloyat: Region.billing_id; tuman: (viloyat, kod) yoki nom, bo'lmasa yaratiladi.
- Xo'jalik (Department): INN yoki nom (tur so'zlarisiz), bo'lmasa yaratiladi (hisobotda).
- Bo'lim (DepartmentBranch): (xo'jalik, nom) bo'yicha get_or_create.
- Turlar: nom (+ parent) bo'yicha, bo'lmasa yaratiladi.
- Ijarachi: JSHSHIR yoki INN bo'yicha birlashtiriladi, bo'lmasa F.I.Sh.+pasport, bo'lmasa yangi.
- Shartnoma: `number` bo'yicha yaratiladi/yangilanadi (qayta ishga tushirish xavfsiz);
  bo'limlari qayta yoziladi; created_at/updated_at eski qiymatlari bilan.
- Fayllar: media/<eski yo'l> -> MEDIA_ROOT/documents/billing/contracts/legacy/<eski yo'l>.
- Tarix: eski sabab -> stat Reason, asl JSON `data.legacy` da.
"""
import json
import os
import re
import shutil
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.billing.management.commands.import_billing_inspectors import _base, _norm
from apps.billing.models import (
    ActivityType, Bolim, Contract, ContractAction, ContractActionProduct, ContractActivity, ContractFile,
    ContractHistory, ContractLand, ContractPrivilege, ContractYearlyAmount, District, LandType, PrivilegeType,
    Region, Renter, Xojalik,
)
from apps.users.models import CustomUser

LEGACY_PREFIX = "documents/billing/contracts/legacy"
TWO = Decimal("0.01")
STATUS_MAP = {"faol": Contract.Status.ACTIVE, "faol emas": Contract.Status.INACTIVE}
REASON_MAP = [
    ("ijarachi", ContractHistory.Reason.RENTER_CHANGED),
    ("xolati", ContractHistory.Reason.STATUS_CHANGED),
    ("holati", ContractHistory.Reason.STATUS_CHANGED),
    ("yillik", ContractHistory.Reason.YEARLY_UPDATED),
    ("fayl qo'shildi", ContractHistory.Reason.FILE_ADDED),
    ("fayl o'chirildi", ContractHistory.Reason.FILE_DELETED),
    ("yaratildi", ContractHistory.Reason.CREATED),
]


def dec(value, places=TWO, default=Decimal("0.00")):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value)).quantize(places)
    except (InvalidOperation, ValueError):
        return default


def dec_or_none(value, places):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value)).quantize(places)
    except (InvalidOperation, ValueError):
        return None


def dt(value):
    if not value:
        return None
    parsed = parse_datetime(str(value))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def digits(value, length):
    v = re.sub(r"\D", "", str(value or ""))
    return v if len(v) == length else None


def map_reason(reason: str):
    r = (reason or "").lower().replace("‘", "'").replace("’", "'")
    for key, mapped in REASON_MAP:
        if key in r:
            return mapped
    return ContractHistory.Reason.UPDATED


class Command(BaseCommand):
    help = "billing-urmon.uz shartnomalarini (bo'limlari, fayllari, tarixi bilan) stat'ga ko'chiradi."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="contracts.json")
        parser.add_argument("--media-root", default=None, help="Eski billing media papkasi (fayllar uchun)")
        parser.add_argument("--dry-run", action="store_true", help="Faqat hisobot, bazaga yozilmaydi")

    # ---------------- helpers ----------------
    def _load(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            raise CommandError(f"JSON o'qilmadi: {e}")

    def _regions(self, rows):
        by_billing = {r.billing_id: r for r in Region.objects.exclude(billing_id__isnull=True)}
        by_name = {_norm(r.name): r for r in Region.objects.all()}
        out = {}
        for row in rows:
            region = by_billing.get(row["id"]) or by_name.get(_norm(row.get("name")))
            if region is None:
                region = next((r for key, r in by_name.items() if _base(row.get("name")) and _base(row.get("name")) in key), None)
            if region is None:
                self.problems.append(f"Viloyat topilmadi: {row.get('name')} (billing id {row['id']})")
            out[row["id"]] = region
        return out

    def _districts(self, rows, regions):
        out = {}
        for row in rows:
            region = regions.get(row.get("region_id"))
            if region is None:
                out[row["id"]] = None
                continue
            obj = None
            if row.get("code"):
                obj = District.objects.filter(region=region, code=str(row["code"]).strip()).first()
            if obj is None and row.get("name"):
                obj = District.objects.filter(region=region, name__iexact=row["name"].strip()).first()
            if obj is None:
                obj = District.objects.create(region=region, code=str(row.get("code") or "").strip()[:10],
                                              name=(row.get("name") or "").strip()[:100])
                self.stats["district_created"] += 1
            out[row["id"]] = obj
        return out

    def _xojaliklar(self, rows, regions):
        by_name, by_inn, by_base = {}, {}, {}
        for x in Xojalik.objects.all():
            by_name[_norm(x.name)] = x
            if x.inn:
                by_inn[x.inn] = x
            by_base.setdefault(_base(x.name), []).append(x)
        out = {}
        for row in rows:
            name = (row.get("name") or "").strip()
            inn = digits(row.get("inn"), 9)
            x = (by_inn.get(inn) if inn else None) or by_name.get(_norm(name))
            if x is None and len(by_base.get(_base(name), [])) == 1:
                x = by_base[_base(name)][0]
            if x is None:
                region = regions.get(row.get("region_id"))
                if region is None or not name:
                    self.problems.append(f"Xo'jalik yaratilmadi (viloyat/nom yo'q): {name} (billing id {row['id']})")
                    out[row["id"]] = None
                    continue
                x = Xojalik.objects.create(
                    name=name[:300], region=region, code=(row.get("code") or None),
                    inn=inn if inn and inn not in by_inn else None,
                    account_detail=row.get("account_detail") or None,
                )
                by_name[_norm(x.name)] = x
                by_base.setdefault(_base(x.name), []).append(x)
                if x.inn:
                    by_inn[x.inn] = x
                self.created_xojaliklar.append(name)
            out[row["id"]] = x
        return out

    def _bolimlar(self, rows, xojaliklar):
        out = {}
        for row in rows:
            x = xojaliklar.get(row.get("department_id"))
            name = (row.get("name") or "").strip()
            if x is None or not name:
                out[row["id"]] = None
                continue
            obj, created = Bolim.objects.get_or_create(xojalik=x, name=name[:150])
            self.stats["bolim_created"] += int(created)
            out[row["id"]] = obj
        return out

    def _types(self, model, rows, extra_fields=()):
        """Avval parent'sizlar, keyin bolalari (old parent_id -> stat obyekt)."""
        out = {}
        pending = sorted(rows, key=lambda r: r.get("parent_id") is not None)
        for row in pending:
            name = (row.get("name") or "").strip()
            if not name:
                out[row["id"]] = None
                continue
            parent = out.get(row.get("parent_id")) if row.get("parent_id") else None
            obj = model.objects.filter(name__iexact=name, parent=parent).first()
            if obj is None:
                obj = model.objects.filter(name__iexact=name).first()
            if obj is None:
                defaults = {f: row.get(f) for f in extra_fields}
                obj = model.objects.create(name=name[:255], parent=parent, description=(row.get("description") or None) and row["description"][:1024], **defaults)
                self.stats["type_created"] += 1
            out[row["id"]] = obj
        return out

    def _renter(self, row):
        pinfl = digits(row.get("pinfl"), 14)
        stir = digits(row.get("stir"), 9) or (digits(row.get("legal_stir"), 9) if row.get("is_legal_entity") else None)
        is_legal = bool(row.get("is_legal_entity"))
        composed = " ".join(p for p in ((row.get("sur_name") or "").strip(), (row.get("first_name") or "").strip(),
                                         (row.get("mid_name") or "").strip()) if p)
        full_name = (row.get("legal_name") if is_legal and row.get("legal_name") else None) \
            or (row.get("full_name") or "").strip() or composed or (row.get("legal_name") or "").strip() \
            or (row.get("username") or "").strip() or "Noma'lum"
        key = ("pinfl", pinfl) if pinfl else (("stir", stir) if stir else None)
        if key and key in self.renter_cache:
            return self.renter_cache[key]

        renter = None
        if pinfl:
            renter = Renter.objects.filter(pinfl=pinfl).first()
        if renter is None and stir:
            renter = Renter.objects.filter(stir=stir).first()
        if renter is None and not pinfl and not stir and row.get("passport"):
            renter = Renter.objects.filter(full_name__iexact=full_name[:255], passport=row["passport"]).first()

        fields = dict(
            full_name=full_name[:255], passport=(row.get("passport") or None), phone=(row.get("phone") or None),
            per_adr=(row.get("per_adr") or row.get("tem_adr") or None), citizenship=(row.get("citizenship") or None),
            birth_place=(row.get("birth_place") or None), is_legal_entity=is_legal,
            legal_name=(row.get("legal_name") or None),
        )
        if renter is None:
            renter = Renter(pinfl=pinfl, stir=stir, **fields)
            renter.save()
            self.stats["renter_created"] += 1
        else:
            for k, v in fields.items():
                if v not in (None, "") and getattr(renter, k) in (None, "", False):
                    setattr(renter, k, v)
            if stir and not renter.stir and not Renter.objects.filter(stir=stir).exclude(pk=renter.pk).exists():
                renter.stir = stir
            if pinfl and not renter.pinfl and not Renter.objects.filter(pinfl=pinfl).exclude(pk=renter.pk).exists():
                renter.pinfl = pinfl
            renter.save()
            self.stats["renter_merged"] += 1
        if key:
            self.renter_cache[key] = renter
        return renter

    # ---------------- contract ----------------
    def _contract(self, row, renters, xojaliklar, bolimlar, regions, districts, types, users):
        number = (row.get("number") or "").strip()
        if not number:
            self.problems.append(f"Shartnoma raqami yo'q: billing id {row.get('id')}")
            return
        xojalik = xojaliklar.get(row.get("department_id"))
        renter = renters.get(row.get("rented_user_id"))
        if xojalik is None or renter is None:
            self.problems.append(f"Shartnoma {number}: xo'jalik yoki ijarachi topilmadi — o'tkazib yuborildi")
            self.stats["contract_skipped"] += 1
            return

        region = regions.get(row.get("region_id")) or xojalik.region
        district = districts.get(row.get("district_id"))
        if district is not None and district.region_id != region.id:
            region = district.region
        status = STATUS_MAP.get((row.get("status") or "").strip().lower(), Contract.Status.ACTIVE)

        values = dict(
            renter=renter, contract_number=(row.get("contract_number") or None), xojalik=xojalik,
            bolim=bolimlar.get(row.get("branch_id")), region=region, district=district,
            contract_date=parse_date(str(row.get("contract_date") or "")) or timezone.localdate(),
            expired_date=parse_date(str(row.get("expired_date") or "")) if row.get("expired_date") else None,
            auction_date=parse_date(str(row.get("auction_date") or "")) if row.get("auction_date") else None,
            exemptioned_date=parse_date(str(row.get("exemptioned_date") or "")) if row.get("exemptioned_date") else None,
            canceled_date=parse_date(str(row.get("canceled_date") or "")) if row.get("canceled_date") else None,
            cancel_reason=(row.get("cancel_reason") or None), status=status,
            rent_amount=dec(row.get("rent_amount")), paid_amount=dec(row.get("paid_amount")),
            penalty_amount=dec(row.get("penalty_amount")), rent_area=dec(row.get("rent_area")),
            cadastral_number=(row.get("cadastral_number") or None), is_entity=bool(row.get("is_entity")),
            circle=(row.get("circle") or None), section=(row.get("section") or None),
            counter=(row.get("counter") or None), massive=(row.get("massive") or None),
            latitude=dec_or_none(row.get("latitude"), Decimal("0.0000001")),
            longitude=dec_or_none(row.get("longitude"), Decimal("0.0000001")),
            boundary_geojson=row.get("boundary_geojson") or None,
        )
        contract = Contract.objects.filter(number=number).first()
        if contract is None:
            contract = Contract(number=number, **values)
            contract.save()
            self.stats["contract_created"] += 1
        else:
            for k, v in values.items():
                setattr(contract, k, v)
            contract.save()
            self.stats["contract_updated"] += 1

        stamps = {}
        if dt(row.get("created_at")):
            stamps["created_at"] = dt(row.get("created_at"))
        if dt(row.get("updated_at")):
            stamps["updated_at"] = dt(row.get("updated_at"))
        if stamps:
            Contract.objects.filter(pk=contract.pk).update(**stamps)

        self._type_rows(contract, ContractActivity, "activities", types["activity"], row.get("activities") or [])
        self._type_rows(contract, ContractLand, "lands", types["land"], row.get("lands") or [])
        self._type_rows(contract, ContractPrivilege, "privileges", types["privilege"], row.get("privileges") or [])
        self._actions(contract, row.get("actions") or [])
        self._yearly(contract, row.get("yearly") or [])
        self._files(contract, row.get("files") or [], users)
        self._history(contract, row.get("history") or [], users)

    def _type_rows(self, contract, model, related, type_map, items):
        getattr(contract, related).all().delete()
        objs = []
        for item in items:
            t = type_map.get(item.get("type_id"))
            if t is None:
                self.problems.append(f"Shartnoma {contract.number}: {model.__name__} turi topilmadi (id {item.get('type_id')})")
                continue
            objs.append(model(contract=contract, type=t, area=dec(item.get("area"))))
        if objs:
            model.objects.bulk_create(objs)

    def _actions(self, contract, items):
        contract.actions.all().delete()
        for item in items:
            action = ContractAction.objects.create(
                contract=contract, vacancy=dec_or_none(item.get("vacancy"), TWO),
                own_investment=dec_or_none(item.get("own_investment"), TWO),
            )
            products = [
                ContractActionProduct(action=action, product_export=p.get("product_export") or None,
                                      product_amount=p.get("product_amount") or None,
                                      export_amount=dec_or_none(p.get("export_amount"), TWO))
                for p in item.get("products") or []
            ]
            if products:
                ContractActionProduct.objects.bulk_create(products)

    def _yearly(self, contract, rows):
        years = []
        for r in rows:
            year = r.get("year")
            if not year:
                continue
            years.append(int(year))
            ContractYearlyAmount.objects.update_or_create(
                contract=contract, year=int(year),
                defaults=dict(contract_amount=dec(r.get("contract_amount")), calculated_amount=dec(r.get("calculated_amount")),
                              paid_amount=dec(r.get("paid_amount")), penalty_amount=dec(r.get("penalty_amount"))),
            )
        contract.yearly_amounts.exclude(year__in=years).delete()

    def _files(self, contract, rows, users):
        for r in rows:
            old_path = (r.get("file") or "").strip().lstrip("/")
            if not old_path:
                continue
            target_name = f"{LEGACY_PREFIX}/{old_path}"
            if ContractFile.objects.filter(contract=contract, file=target_name).exists():
                continue
            source = os.path.join(self.media_root, old_path) if self.media_root else None
            if not source or not os.path.isfile(source):
                self.missing_files.append((contract.number, old_path))
                continue
            if not self.dry_run:
                dest = os.path.join(settings.MEDIA_ROOT, target_name)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if not os.path.exists(dest):
                    shutil.copy2(source, dest)
            obj = ContractFile(contract=contract, description=(r.get("description") or "")[:500] or None,
                               uploaded_by=users.get((r.get("uploaded_by") or "").lower()))
            obj.file.name = target_name
            obj.save()
            if dt(r.get("created_at")):
                ContractFile.objects.filter(pk=obj.pk).update(created_at=dt(r.get("created_at")))
            self.stats["file_created"] += 1

    def _history(self, contract, rows, users):
        contract.history.filter(data__has_key="legacy_reason").delete()
        for r in rows:
            obj = ContractHistory.objects.create(
                contract=contract, executor=users.get((r.get("executor") or "").lower()),
                reason=map_reason(r.get("reason")),
                data={"legacy_reason": r.get("reason"), "legacy": r.get("history")},
            )
            if dt(r.get("created_at")):
                ContractHistory.objects.filter(pk=obj.pk).update(created_at=dt(r.get("created_at")))
            self.stats["history_created"] += 1

    # ---------------- main ----------------
    def handle(self, *args, **options):
        data = self._load(options["file"])
        self.dry_run = options["dry_run"]
        self.media_root = options["media_root"]
        self.stats = {k: 0 for k in (
            "district_created", "bolim_created", "type_created", "renter_created", "renter_merged",
            "contract_created", "contract_updated", "contract_skipped", "file_created", "history_created")}
        self.problems, self.created_xojaliklar, self.missing_files, self.renter_cache = [], [], [], {}

        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — bazaga yozilmaydi, fayllar ko'chirilmaydi"))
        if not self.media_root:
            self.stdout.write(self.style.WARNING("--media-root berilmagan: fayllar ko'chirilmaydi"))

        users = {u.username.lower(): u for u in CustomUser.objects.exclude(username__isnull=True).exclude(username="")}

        with transaction.atomic():
            regions = self._regions(data.get("regions") or [])
            districts = self._districts(data.get("districts") or [], regions)
            xojaliklar = self._xojaliklar(data.get("departments") or [], regions)
            bolimlar = self._bolimlar(data.get("branches") or [], xojaliklar)
            types = {
                "activity": self._types(ActivityType, data.get("activity_types") or []),
                "land": self._types(LandType, data.get("land_types") or []),
                "privilege": self._types(PrivilegeType, data.get("privilege_types") or [], extra_fields=("month",)),
            }
            renters = {row["id"]: self._renter(row) for row in data.get("renters") or []}

            contracts = data.get("contracts") or []
            for i, row in enumerate(contracts, 1):
                self._contract(row, renters, xojaliklar, bolimlar, regions, districts, types, users)
                if i % 500 == 0:
                    self.stdout.write(f"  ... {i}/{len(contracts)}")

            if self.dry_run:
                transaction.set_rollback(True)

        s = self.stats
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"{'DRY RUN — ' if self.dry_run else ''}shartnomalar: yaratildi {s['contract_created']}, "
            f"yangilandi {s['contract_updated']}, o'tkazib yuborildi {s['contract_skipped']}"))
        self.stdout.write(
            f"ijarachilar: yangi {s['renter_created']}, mavjudga birlashtirildi {s['renter_merged']}; "
            f"tumanlar yaratildi {s['district_created']}; bo'limlar yaratildi {s['bolim_created']}; "
            f"turlar yaratildi {s['type_created']}; fayllar {s['file_created']}; tarix yozuvlari {s['history_created']}")
        if self.created_xojaliklar:
            self.stdout.write(self.style.WARNING(
                f"Yangi yaratilgan xo'jaliklar ({len(self.created_xojaliklar)}): {', '.join(self.created_xojaliklar)}"))
        if self.missing_files:
            self.stdout.write(self.style.WARNING(f"Topilmagan fayllar ({len(self.missing_files)}):"))
            for number, path in self.missing_files[:50]:
                self.stdout.write(f"  {number}: {path}")
            if len(self.missing_files) > 50:
                self.stdout.write(f"  ... yana {len(self.missing_files) - 50} ta")
        if self.problems:
            self.stdout.write(self.style.WARNING(f"Muammolar ({len(self.problems)}):"))
            for p in self.problems[:50]:
                self.stdout.write(f"  {p}")
            if len(self.problems) > 50:
                self.stdout.write(f"  ... yana {len(self.problems) - 50} ta")
