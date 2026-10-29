"""
Yuklama sinovi uchun sintetik ma'lumot (TZ §17.3, Q35: 100 000 buyurtma, 100 faol foydalanuvchi).

    python manage.py yashil_seed_load --orders 100000 --users 100 --password '<parol>' --tokens-out /tmp/load-tokens.json
    python manage.py yashil_seed_load --tokens-only --tokens-out /tmp/load-tokens.json   # tokenlarni yangilash (15 daqiqa)
    python manage.py yashil_seed_load --purge                                           # hammasini o'chirish

Faqat lokal/test muhitda: DEBUG=True yoki `--force` bilan birga YASHIL_ALLOW_LOAD_SEED=1.
Belgilar: mahalla `LOAD-…`, tashkilot/bo'linma nomi `LOAD …`, buyurtma `LD-…`,
foydalanuvchi `load.*@load.test` — `--purge` faqat shularni o'chiradi.
Tumanlar va katalog mavjud ma'lumotnomadan olinadi (lokalda avval `yashil_seed_demo`).
"""
import json
import os
import random
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_tz
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.billing.models import District
from apps.general.models import Organization
from apps.yashil.models import (
    Acceptance, Act, ActLine, ActVersion, CatalogItem, Mahalla, MahallaUnionRoute, Order, OrderEvent, OrderLine,
    OrderState, ReviewSegment, ServiceAllocation, StockMovement, SupplierAssignment, SupplierProfile, UnionUnit,
    Warehouse, YashilMembership,
)

User = get_user_model()
T = YashilMembership.MemberType
S = OrderState
MAHALLA_PREFIX, ORG_PREFIX, ORDER_PREFIX, EMAIL_DOMAIN = "LOAD-", "LOAD ", "LD-", "@load.test"
VALID_FROM = date(2026, 1, 1)
# TZ §7 holatlari bo'yicha taxminiy taqsimot (ishchi yil o'rtasi)
STATE_WEIGHTS = [
    (S.DRAFT, 5), (S.UNION_NEW, 8), (S.UNION_REVIEW, 4), (S.RETURNED, 4), (S.SUPPLIER_NEW, 8), (S.SUPPLIER_REVIEW, 4),
    (S.EXECUTION, 30), (S.PARTIAL, 12), (S.CLOSED, 23), (S.CANCELLED, 2),
]
ACCEPTED = {S.EXECUTION, S.PARTIAL, S.CLOSED}
# Foydalanuvchilar: kabinet turi → ulush (100 tadan)
USER_SPLIT = [("mahalla", 50), ("union", 15), ("forest", 20), ("dm", 5), ("observer", 10)]


def _aware(d: date, hour: int = 10) -> datetime:
    return datetime.combine(d, time(hour, 0), tzinfo=dt_tz.utc)


class Command(BaseCommand):
    help = "Yashil mahalla: yuklama sinovi uchun sintetik buyurtmalar va foydalanuvchilar (faqat test muhit)"

    def add_arguments(self, parser):
        parser.add_argument("--orders", type=int, default=100_000)
        parser.add_argument("--mahallas", type=int, default=2000)
        parser.add_argument("--forests", type=int, default=40)
        parser.add_argument("--dms", type=int, default=6)
        parser.add_argument("--districts", type=int, default=40, help="Mavjud tumanlardan nechtasi ishlatiladi")
        parser.add_argument("--users", type=int, default=100)
        parser.add_argument("--password", default="", help="Sintetik foydalanuvchilar paroli (yaratishda majburiy)")
        parser.add_argument("--tokens-out", default="", help="Yuklama skripti uchun JWT tokenlar (JSON)")
        parser.add_argument("--tokens-only", action="store_true", help="Faqat tokenlarni qayta yozish")
        parser.add_argument("--purge", action="store_true", help="Sintetik ma'lumotni o'chirish")
        parser.add_argument("--batch", type=int, default=5000)
        parser.add_argument("--seed", type=int, default=20261029)
        parser.add_argument("--force", action="store_true", help="DEBUG=False muhitda (YASHIL_ALLOW_LOAD_SEED=1 ham kerak)")

    def handle(self, *args, **o):
        if not settings.DEBUG and not (o["force"] and os.environ.get("YASHIL_ALLOW_LOAD_SEED") == "1"):
            raise CommandError("Faqat test muhit: DEBUG=True yoki --force va YASHIL_ALLOW_LOAD_SEED=1")
        if o["purge"]:
            self.stdout.write(json.dumps(purge(), ensure_ascii=False))
            return
        if o["tokens_only"]:
            if not o["tokens_out"]:
                raise CommandError("--tokens-out kerak")
            n = write_tokens(o["tokens_out"])
            self.stdout.write(f"Tokenlar: {n} → {o['tokens_out']}")
            return
        if not o["password"]:
            raise CommandError("--password kerak (sintetik foydalanuvchilar uchun)")
        if Order.objects.filter(number__startswith=ORDER_PREFIX).exists():
            raise CommandError("Sintetik ma'lumot allaqachon bor — avval --purge")
        rnd = random.Random(o["seed"])
        started = timezone.now()
        world = build_world(rnd, o)
        self.stdout.write(f"Ma'lumotnoma: {len(world['mahallas'])} mahalla, {len(world['forests'])} xo'jalik, {len(world['dms'])} DM")
        made = 0
        while made < o["orders"]:
            n = min(o["batch"], o["orders"] - made)
            with transaction.atomic():
                build_orders(rnd, world, start=made, count=n)
            made += n
            self.stdout.write(f"  buyurtmalar: {made}/{o['orders']}")
        finalize_stock(world)
        from apps.yashil.services.stats import bump_version

        bump_version()
        if o["tokens_out"]:
            write_tokens(o["tokens_out"])
        self.stdout.write(f"Tayyor: {made} buyurtma, {(timezone.now() - started).seconds} s")


# ----------------------------------------------------------------------------- ma'lumotnoma
def build_world(rnd, o) -> dict:
    districts = list(District.objects.select_related("region").order_by("code")[: o["districts"]])
    if not districts:
        raise CommandError("billing tumanlari yo'q — avval ma'lumotnomani (yoki yashil_seed_demo) yuklang")
    forest_items = list(CatalogItem.objects.filter(is_active=True, supplier_type="forest", item_type="goods"))
    dm_items = list(CatalogItem.objects.filter(is_active=True, supplier_type="dm"))
    if not forest_items or not dm_items:
        raise CommandError("Faol katalog yo'q (o'rmon va DM) — avval katalogni yuklang")
    regions = {d.region_id: d.region for d in districts}

    with transaction.atomic():
        units = {d.id: UnionUnit.objects.create(name=f"{ORG_PREFIX}уюшма {d.name}", level=UnionUnit.Level.DISTRICT,
                                                region=d.region, district=d) for d in districts}
        forests, dms = [], []
        for i in range(1, o["forests"] + 1):
            org = Organization.objects.create(name=f"{ORG_PREFIX}Ўрмон хўжалиги {i:03d}", region="toshkent")
            SupplierProfile.objects.create(organization=org, supplier_type=SupplierProfile.SupplierType.FOREST)
            forests.append(org)
        for i in range(1, o["dms"] + 1):
            org = Organization.objects.create(name=f"{ORG_PREFIX}ДМ {i:02d}", region="toshkent")
            profile = SupplierProfile.objects.create(organization=org, supplier_type=SupplierProfile.SupplierType.DM)
            profile.service_regions.set(regions.values())
            dms.append(org)
        warehouses = {org.id: Warehouse.objects.create(organization=org, name="Асосий омбор") for org in forests + dms}

        mahallas = Mahalla.objects.bulk_create([
            Mahalla(name=f"Юклама маҳалла {i:05d}", region=districts[i % len(districts)].region, district=districts[i % len(districts)],
                    source_code=f"{MAHALLA_PREFIX}{i:06d}", valid_from=VALID_FROM)
            for i in range(1, o["mahallas"] + 1)
        ])
        SupplierAssignment.objects.bulk_create([
            SupplierAssignment(mahalla=m, organization=forests[i % len(forests)], valid_from=VALID_FROM) for i, m in enumerate(mahallas)
        ])
        MahallaUnionRoute.objects.bulk_create([
            MahallaUnionRoute(mahalla=m, union_unit=units[m.district_id], valid_from=VALID_FROM) for m in mahallas
        ])
        creator = User.objects.create_user(email=f"load.creator{EMAIL_DOMAIN}", password=o["password"], first_name="Load",
                                           last_name="Creator", role="ym_mahalla")
        creators = {m.id: c for m, c in zip(mahallas, YashilMembership.objects.bulk_create([
            YashilMembership(user=creator, member_type=T.MAHALLA, mahalla=m, can_prepare=True, can_sign=True, valid_from=VALID_FROM)
            for m in mahallas
        ]))}
        _make_users(rnd, o, mahallas, list(units.values()), forests, dms)
    assigned = {m.id: forests[i % len(forests)] for i, m in enumerate(mahallas)}
    return {"assigned": assigned, "districts": districts, "units": units, "forests": forests, "dms": dms, "warehouses": warehouses,
            "mahallas": mahallas, "creators": creators, "creator_user": creator,
            "forest_items": forest_items, "dm_items": dm_items}


def _make_users(rnd, o, mahallas, units, forests, dms):
    total = o["users"]
    scale = total / sum(n for _, n in USER_SPLIT)
    targets = {"mahalla": mahallas, "union": units, "forest": forests, "dm": dms, "observer": [None]}
    roles = {"mahalla": "ym_mahalla", "union": "ym_union", "forest": "tashkilot_hodimi", "dm": "tashkilot_hodimi", "observer": "ym_observer"}
    counts = {kind: max(1, int(share * scale)) for kind, share in USER_SPLIT}
    counts["mahalla"] += max(0, total - sum(counts.values()))
    for kind, _ in USER_SPLIT:
        for i in range(1, counts[kind] + 1):
            target = targets[kind][(i - 1) % len(targets[kind])]
            extra = {"organization": target} if kind in ("forest", "dm") else {}
            user = User.objects.create_user(email=f"load.{kind}.{i:03d}{EMAIL_DOMAIN}", password=o["password"],
                                            first_name="Load", last_name=f"{kind.title()} {i:03d}", role=roles[kind], **extra)
            m = {"user": user, "valid_from": VALID_FROM, "can_prepare": kind != "observer", "can_sign": kind in ("mahalla", "forest", "dm")}
            if kind == "mahalla":
                m.update(member_type=T.MAHALLA, mahalla=target)
            elif kind == "union":
                m.update(member_type=T.UNION, union_unit=target)
            elif kind == "observer":
                m.update(member_type=T.OBSERVER)
            else:
                m.update(member_type=T.SUPPLIER, organization=target)
            YashilMembership.objects.create(**m)


# ----------------------------------------------------------------------------- buyurtmalar
def _state(rnd):
    return rnd.choices([s for s, _ in STATE_WEIGHTS], weights=[w for _, w in STATE_WEIGHTS])[0]


def build_orders(rnd, world, *, start: int, count: int):
    today = date.today()
    orders, lines_by_order = [], {}
    for k in range(start, start + count):
        mahalla = world["mahallas"][rnd.randrange(len(world["mahallas"]))]
        route = "forest" if rnd.random() < 0.8 else "dm"
        if route == "forest":
            supplier = world["assigned"][mahalla.id]
        else:
            supplier = world["dms"][rnd.randrange(len(world["dms"]))]
        state = _state(rnd)
        submitted = today - timedelta(days=rnd.randint(1, 300))
        o = Order(
            number=f"{ORDER_PREFIX}{submitted.year}-{k + 1:07d}", mahalla=mahalla, route=route, supplier_org=supplier,
            union_unit=world["units"][mahalla.district_id], state=state, title=f"Юклама буюртма {k + 1}",
            address=f"{mahalla.name}, {rnd.randint(1, 120)}-уй", lat=Decimal(f"{rnd.uniform(39.0, 42.0):.6f}"),
            lon=Decimal(f"{rnd.uniform(64.0, 71.0):.6f}"), area_ha=Decimal(f"{rnd.uniform(0.1, 5):.4f}"),
            created_by_membership=world["creators"][mahalla.id], base_seedlings=rnd.randint(10, 500) if route == "dm" else None,
        )
        if state != S.DRAFT:
            o.first_submitted_at = o.last_submitted_at = _aware(submitted)
        if state in (S.UNION_NEW, S.UNION_REVIEW, S.SUPPLIER_NEW, S.SUPPLIER_REVIEW):
            o.review_due = submitted + timedelta(days=5)
            if o.review_due < today:
                o.late_workdays, o.overdue_stage = rnd.randint(1, 30), "review"
        if state in ACCEPTED:
            accepted = submitted + timedelta(days=rnd.randint(1, 4))
            o.accepted_at, o.accepted_on = _aware(accepted, 11), accepted
            o.delivery_due = accepted + timedelta(days=14)
            o.executor_name = "Юклама ижрочи"
            if state != S.CLOSED and o.delivery_due < today and rnd.random() < 0.3:
                o.late_workdays, o.overdue_stage = rnd.randint(1, 40), "delivery"
        if state in (S.CLOSED, S.CANCELLED):
            o.closed_at = _aware(submitted + timedelta(days=rnd.randint(5, 30)), 15)
        items = world["forest_items"] if route == "forest" else world["dm_items"]
        chosen = rnd.sample(items, k=min(len(items), rnd.randint(1, 3)))
        lines_by_order[o.number] = [(item, Decimal(rnd.randint(1, 60) * 10)) for item in chosen]
        orders.append(o)
    Order.objects.bulk_create(orders, batch_size=2000)

    lines = []
    for o in orders:
        for pos, (item, qty) in enumerate(lines_by_order[o.number]):
            lines.append(OrderLine(order=o, catalog_item=item, qty=qty, position=pos))
    OrderLine.objects.bulk_create(lines, batch_size=5000)
    lines_of = {}
    for line in lines:
        lines_of.setdefault(line.order_id, []).append(line)

    creator = world["creator_user"]
    segments, events, acceptances = [], [], []
    for o in orders:
        if o.first_submitted_at:
            d = o.first_submitted_at.date()
            segments.append(ReviewSegment(order=o, started_on=d, ended_on=o.accepted_on, ended_reason="accepted" if o.accepted_on else ""))
            events.append(OrderEvent(order=o, action="submit", from_state="draft", to_state="union_new", actor_user=creator))
        if o.accepted_on:
            events.append(OrderEvent(order=o, action="accept", from_state="supplier_review", to_state="execution", actor_user=creator))
            acceptances.append(Acceptance(order=o, warehouse=world["warehouses"][o.supplier_org_id], accepted_by=creator,
                                          accepted_on=o.accepted_on, delivery_due=o.delivery_due, executor_name=o.executor_name))
    ReviewSegment.objects.bulk_create(segments, batch_size=5000)
    OrderEvent.objects.bulk_create(events, batch_size=5000)
    Acceptance.objects.bulk_create(acceptances, batch_size=2000)

    moves, services, acts, versions, act_lines = [], [], [], [], []
    for acc in acceptances:
        o = acc.order
        for line in lines_of[o.id]:
            if line.catalog_item.item_type == CatalogItem.ItemType.SERVICE:
                services.append(ServiceAllocation(organization_id=o.supplier_org_id, catalog_item=line.catalog_item,
                                                  period=o.accepted_on.strftime("%Y-%m"), acceptance=acc, order_line=line, qty=line.qty))
            else:
                moves.append(StockMovement(warehouse=acc.warehouse, catalog_item=line.catalog_item, kind=StockMovement.Kind.ALLOCATE,
                                           qty=-line.qty, acceptance=acc, order_line=line, doc_number=o.number, doc_date=o.accepted_on))
        if o.state in (S.PARTIAL, S.CLOSED):
            act = Act(order=o, index=1, number=f"{o.number}/A1", status=Act.Status.APPROVED, is_partial=o.state == S.PARTIAL,
                      approved_at=o.closed_at or o.accepted_at)
            version = ActVersion(act=act, version_no=1, delivery_date=o.accepted_on + timedelta(days=3), responsible="Юклама",
                                 submitted_at=o.accepted_at)
            acts.append(act)
            versions.append(version)
            for line in lines_of[o.id]:
                qty = line.qty if o.state == S.CLOSED else (line.qty / 2).quantize(Decimal("1"))
                act_lines.append(ActLine(act_version=version, order_line=line, qty=qty))
    StockMovement.objects.bulk_create(moves, batch_size=5000)
    ServiceAllocation.objects.bulk_create(services, batch_size=5000)
    Act.objects.bulk_create(acts, batch_size=2000)
    ActVersion.objects.bulk_create(versions, batch_size=2000)
    ActLine.objects.bulk_create(act_lines, batch_size=5000)
    for act, version in zip(acts, versions):
        act.current_version = version
    Act.objects.bulk_update(acts, ["current_version"], batch_size=2000)


@transaction.atomic
def finalize_stock(world):
    """DM ombori manfiy bo'lmaydi (TZ §9.2): ajratilganidan ko'p boshlang'ich qoldiq; xizmatlarga oylik quvvat.
    O'rmon xo'jaliklarining yarmiga boshlang'ich qoldiq (qolganlari manfiyda — TZ bo'yicha ruxsat)."""
    from django.db.models import Sum

    from apps.yashil.models import ServiceCapacity

    openings = []
    for i, org in enumerate(world["dms"] + world["forests"]):
        if org in world["forests"] and i % 2:
            continue
        wh = world["warehouses"][org.id]
        allocated = dict(StockMovement.objects.filter(warehouse=wh, kind=StockMovement.Kind.ALLOCATE)
                         .values_list("catalog_item").annotate(s=Sum("qty")).values_list("catalog_item", "s"))
        for item_id, total in allocated.items():
            openings.append(StockMovement(warehouse=wh, catalog_item_id=item_id, kind=StockMovement.Kind.OPENING, qty=-total + 1000,
                                          doc_number="LOAD-ИНВ", doc_date=VALID_FROM - timedelta(days=1)))
    StockMovement.objects.bulk_create(openings, batch_size=5000)
    used = (ServiceAllocation.objects.filter(organization__in=world["dms"]).values("organization", "catalog_item", "period")
            .annotate(s=Sum("qty")))
    ServiceCapacity.objects.bulk_create([
        ServiceCapacity(organization_id=r["organization"], catalog_item_id=r["catalog_item"], period=r["period"], capacity=r["s"] + 100)
        for r in used
    ], batch_size=5000)


# ----------------------------------------------------------------------------- tokenlar va tozalash
def write_tokens(path: str) -> int:
    from rest_framework_simplejwt.tokens import AccessToken

    rows = []
    now = timezone.now()
    for m in (YashilMembership.objects.filter(user__email__endswith=EMAIL_DOMAIN).exclude(user__email=f"load.creator{EMAIL_DOMAIN}")
              .select_related("user").order_by("user__email")):
        User.objects.filter(pk=m.user_id).update(last_activity=now)
        rows.append({"email": m.user.email, "kind": m.user.email.split(".")[1], "cabinet": str(m.id),
                     "token": str(AccessToken.for_user(m.user))})
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    os.chmod(path, 0o600)
    return len(rows)


def _raw_delete(qs) -> int:
    return qs._raw_delete(qs.db)


def purge() -> dict:
    orders = Order.objects.filter(number__startswith=ORDER_PREFIX)
    acts = Act.objects.filter(order__in=orders)
    out = {}
    with transaction.atomic():
        out["act_lines"] = _raw_delete(ActLine.objects.filter(act_version__act__in=acts))
        Act.objects.filter(order__in=orders).update(current_version=None)
        out["act_versions"] = _raw_delete(ActVersion.objects.filter(act__in=acts))
        out["acts"] = _raw_delete(acts)
        out["stock_movements"] = _raw_delete(StockMovement.objects.filter(order_line__order__in=orders))
        out["stock_movements"] += _raw_delete(StockMovement.objects.filter(warehouse__organization__name__startswith=ORG_PREFIX))
        from apps.yashil.models import ServiceCapacity

        _raw_delete(ServiceCapacity.objects.filter(organization__name__startswith=ORG_PREFIX))
        out["service_allocations"] = _raw_delete(ServiceAllocation.objects.filter(order_line__order__in=orders))
        out["acceptances"] = _raw_delete(Acceptance.objects.filter(order__in=orders))
        out["events"] = _raw_delete(OrderEvent.objects.filter(order__in=orders))
        out["segments"] = _raw_delete(ReviewSegment.objects.filter(order__in=orders))
        out["lines"] = _raw_delete(OrderLine.objects.filter(order__in=orders))
        out["orders"] = _raw_delete(orders)
        mahallas = Mahalla.objects.filter(source_code__startswith=MAHALLA_PREFIX)
        orgs = Organization.objects.filter(name__startswith=ORG_PREFIX)
        users = User.objects.filter(email__endswith=EMAIL_DOMAIN)
        out["memberships"] = _raw_delete(YashilMembership.objects.filter(user__in=users))
        _raw_delete(SupplierAssignment.objects.filter(mahalla__in=mahallas))
        _raw_delete(MahallaUnionRoute.objects.filter(mahalla__in=mahallas))
        out["mahallas"] = _raw_delete(mahallas)
        _raw_delete(UnionUnit.objects.filter(name__startswith=ORG_PREFIX))
        _raw_delete(Warehouse.objects.filter(organization__in=orgs))
        SupplierProfile.service_regions.through.objects.filter(supplierprofile__organization__in=orgs).delete()
        _raw_delete(SupplierProfile.objects.filter(organization__in=orgs))
        out["users"] = users.delete()[0]
        out["organizations"] = orgs.delete()[0]
    from apps.yashil.services.stats import bump_version

    bump_version()
    return out
