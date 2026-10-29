"""
Kabinet va ko'lam (TZ §2 jadval, §2.2).

    memberships_for(user)            -> QuerySet[YashilMembership]  (faol, amaldagi)
    is_module_admin(user)            -> bool
    resolve_cabinet(user, header)    -> YashilMembership | None     (header yot bo'lsa CabinetForbidden)
    visible_mahalla_ids(membership)  -> set[UUID] | None            None = cheklovsiz

Qoidalar:
- mahalla a'zosi — faqat o'z mahallasi;
- uyushma a'zosi — faol marshrut bo'yicha unga tegishli mahallalar;
- o'rmon xo'jaligi — faol biriktirilgan mahallalar;
- DM — xizmat hududi (viloyat/tuman) bo'yicha; hudud ko'rsatilmagan bo'lsa cheklovsiz;
- kuzatuvchi — `observer_scope` ({} = respublika);
- modul admini (super_admin/superuser/`yashil.manage_module`) a'zoliksiz — cheklovsiz.
"""
from datetime import date

from django.db.models import Exists, OuterRef, Q

from apps.yashil.models import Mahalla, MahallaUnionRoute, SupplierAssignment, SupplierProfile, YashilMembership

MODULE_ADMIN_PERM = "yashil.manage_module"
NOT_ASSIGNED_FOREST = "Хўжалик бириктирилмаган"
NOT_ROUTED_UNION = "Уюшма бўлинмаси бириктирилмаган"


class CabinetForbidden(Exception):
    """So'ralgan kabinet foydalanuvchiga tegishli emas."""


def _active_period_q(on: date) -> Q:
    return Q(valid_from__lte=on) & (Q(valid_to__isnull=True) | Q(valid_to__gte=on))


def is_module_admin(user) -> bool:
    if not (user and getattr(user, "is_authenticated", False)):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "role", None) == "super_admin":
        return True
    return user.has_perm(MODULE_ADMIN_PERM)


def memberships_for(user, on: date | None = None):
    if not (user and getattr(user, "is_authenticated", False)):
        return YashilMembership.objects.none()
    on = on or date.today()
    return (
        YashilMembership.objects.filter(user=user, is_active=True)
        .filter(_active_period_q(on))
        .select_related("mahalla__district__region", "union_unit", "organization__supplier_profile")
        .order_by("member_type", "created_at")
    )


def resolve_cabinet(user, header_value: str | None):
    """Faol kabinet: header'dagi a'zolik (foydalanuvchiniki bo'lsa) yoki birinchisi."""
    qs = memberships_for(user)
    if header_value:
        cabinet = qs.filter(pk=header_value).first()
        if cabinet is None:
            raise CabinetForbidden()
        return cabinet
    return qs.first()


def primary_forest_assignment(mahalla, on: date | None = None):
    on = on or date.today()
    return (
        SupplierAssignment.objects.filter(mahalla=mahalla).filter(_active_period_q(on))
        .select_related("organization__supplier_profile").first()
    )


def union_route(mahalla, on: date | None = None):
    on = on or date.today()
    return MahallaUnionRoute.objects.filter(mahalla=mahalla).filter(_active_period_q(on)).select_related("union_unit").first()


def visible_mahalla_ids(membership, on: date | None = None):
    """Ko'rinadigan mahallalar ID to'plami yoki None (cheklovsiz)."""
    if membership is None:
        return None
    on = on or date.today()
    T = YashilMembership.MemberType
    if membership.member_type == T.MAHALLA:
        return {membership.mahalla_id}
    if membership.member_type == T.UNION:
        return set(
            MahallaUnionRoute.objects.filter(union_unit_id=membership.union_unit_id)
            .filter(_active_period_q(on)).values_list("mahalla_id", flat=True)
        )
    if membership.member_type == T.SUPPLIER:
        profile = SupplierProfile.objects.filter(organization_id=membership.organization_id).first()
        if profile is None:
            return set()
        if profile.supplier_type == SupplierProfile.SupplierType.FOREST:
            return set(
                SupplierAssignment.objects.filter(organization_id=membership.organization_id)
                .filter(_active_period_q(on)).values_list("mahalla_id", flat=True)
            )
        region_ids = list(profile.service_regions.values_list("id", flat=True))
        district_ids = list(profile.service_districts.values_list("id", flat=True))
        if not region_ids and not district_ids:
            return None
        return set(
            Mahalla.objects.filter(Q(region_id__in=region_ids) | Q(district_id__in=district_ids))
            .values_list("id", flat=True)
        )
    if membership.member_type == T.OBSERVER:
        scope = membership.observer_scope or {}
        regions = scope.get("regions") or []
        districts = scope.get("districts") or []
        if not regions and not districts:
            return None
        return set(
            Mahalla.objects.filter(Q(region__code__in=regions) | Q(district__code__in=districts))
            .values_list("id", flat=True)
        )
    return set()


def scope_mahallas(queryset, membership, field: str = "id"):
    ids = visible_mahalla_ids(membership)
    if ids is None:
        return queryset
    if not ids:
        return queryset.none()
    return queryset.filter(**{f"{field}__in": ids})


def mahalla_visible(mahalla_id, membership) -> bool:
    ids = visible_mahalla_ids(membership)
    return ids is None or mahalla_id in ids


def dm_suppliers_for(mahalla):
    """Mahalla hududiga xizmat ko'rsatadigan faol DM'lar (hudud ko'rsatilmaganlar ham)."""
    return (
        SupplierProfile.objects.filter(supplier_type=SupplierProfile.SupplierType.DM, is_active_supplier=True)
        .filter(
            Q(service_regions__isnull=True, service_districts__isnull=True)
            | Q(service_regions=mahalla.region_id)
            | Q(service_districts=mahalla.district_id)
        )
        .select_related("organization").distinct().order_by("organization__name")
    )


def forest_suppliers(exclude_org_id=None):
    qs = SupplierProfile.objects.filter(
        supplier_type=SupplierProfile.SupplierType.FOREST, is_active_supplier=True
    ).select_related("organization").order_by("organization__name")
    if exclude_org_id:
        qs = qs.exclude(organization_id=exclude_org_id)
    return qs


def memberships_active_for_target(member_type, *, mahalla_id=None, union_unit_id=None, organization_id=None, on: date | None = None):
    """Xabarnoma qabul qiluvchilar: berilgan kabinetning faol a'zolari."""
    on = on or date.today()
    qs = YashilMembership.objects.filter(member_type=member_type, is_active=True, user__is_active=True).filter(_active_period_q(on))
    if mahalla_id is not None:
        qs = qs.filter(mahalla_id=mahalla_id)
    if union_unit_id is not None:
        qs = qs.filter(union_unit_id=union_unit_id)
    if organization_id is not None:
        qs = qs.filter(organization_id=organization_id)
    return qs.select_related("user")


# ----------------------------------------------------------------------------- buyurtmalar ko'lami
UNION_VISIBLE_EXCLUDE = ("draft",)


def orders_for_cabinet(cabinet, is_admin: bool):
    """Kabinet ko'lamidagi buyurtmalar (TZ §2 jadvali)."""
    from apps.yashil.models import Order, OrderEvent, OrderState

    T = YashilMembership.MemberType
    qs = Order.objects.select_related("mahalla__district", "mahalla__region", "supplier_org__supplier_profile", "union_unit")
    if cabinet is None:
        return qs if is_admin else qs.none()
    if cabinet.member_type == T.MAHALLA:
        return qs.filter(mahalla_id=cabinet.mahalla_id)
    if cabinet.member_type == T.UNION:
        return qs.filter(union_unit_id=cabinet.union_unit_id).exclude(state__in=UNION_VISIBLE_EXCLUDE)
    if cabinet.member_type == T.SUPPLIER:
        forwarded = OrderEvent.objects.filter(order=OuterRef("pk"), action="forward")
        return qs.filter(supplier_org_id=cabinet.organization_id).annotate(_fw=Exists(forwarded)).filter(
            Q(state__in=(OrderState.SUPPLIER_NEW, OrderState.SUPPLIER_REVIEW, OrderState.EXECUTION, OrderState.PARTIAL, OrderState.CLOSED)) | Q(_fw=True)
        ).exclude(state=OrderState.DRAFT)
    if cabinet.member_type == T.OBSERVER:
        return scope_mahallas(qs, cabinet, field="mahalla_id").exclude(state=OrderState.DRAFT)
    return qs.none()
