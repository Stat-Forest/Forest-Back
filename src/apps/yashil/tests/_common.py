"""Yashil testlari uchun yordamchilar (fayl nomi `test*` emas)."""
from datetime import date

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.models import District, Region
from apps.general.models import Organization
from apps.yashil.models import (
    CatalogItem,
    Mahalla,
    MahallaUnionRoute,
    SupplierAssignment,
    SupplierProfile,
    UnionUnit,
    YashilMembership,
)

User = get_user_model()
BASE = "/api/v1/yashil"


def make_user(name: str, role: str = "tashkilot_hodimi", **extra):
    return User.objects.create_user(
        email=f"{name}@example.com", password="TestPassword123!",
        first_name="T", last_name=name.title(), role=role, **extra,
    )


def auth(client, user, cabinet=None):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}
    if cabinet is not None:
        headers["HTTP_X_YASHIL_CABINET"] = str(cabinet.pk)
    client.credentials(**headers)
    return client


def make_region(code="1703", name="Андижон вилояти"):
    region, _ = Region.objects.get_or_create(code=code, defaults={"name": name})
    return region


def make_district(region, code="1703202", name="Андижон тумани"):
    district, _ = District.objects.get_or_create(region=region, code=code, defaults={"name": name})
    return district


def make_mahalla(district, name="Боғистон маҳалласи", source_code=None):
    return Mahalla.objects.create(
        name=name, region=district.region, district=district,
        source_code=source_code or f"MH-{name[:6]}-{Mahalla.objects.count() + 1}",
    )


def make_org(name, region="andijon", **extra):
    return Organization.objects.create(name=name, region=region, **extra)


def make_forest(name="Намуна ўрмон хўжалиги", **extra):
    org = make_org(name)
    SupplierProfile.objects.create(organization=org, supplier_type=SupplierProfile.SupplierType.FOREST, **extra)
    return org


def make_dm(name="Яшил боғлар ДМ", parent=None, **extra):
    org = make_org(name)
    profile = SupplierProfile.objects.create(
        organization=org, supplier_type=SupplierProfile.SupplierType.DM,
        parent=parent.supplier_profile if parent else None, **extra,
    )
    return org, profile


def assign_forest(mahalla, org, valid_from=date(2026, 1, 1), valid_to=None):
    return SupplierAssignment.objects.create(mahalla=mahalla, organization=org, valid_from=valid_from, valid_to=valid_to)


def make_union(district, name="Андижон туман уюшмаси"):
    return UnionUnit.objects.create(name=name, level=UnionUnit.Level.DISTRICT, region=district.region, district=district)


def route_union(mahalla, unit, valid_from=date(2026, 1, 1), valid_to=None):
    return MahallaUnionRoute.objects.create(mahalla=mahalla, union_unit=unit, valid_from=valid_from, valid_to=valid_to)


def member(user, member_type, *, mahalla=None, union_unit=None, organization=None, **extra):
    extra.setdefault("can_prepare", True)
    extra.setdefault("can_sign", True)
    return YashilMembership.objects.create(
        user=user, member_type=member_type, mahalla=mahalla, union_unit=union_unit,
        organization=organization, **extra,
    )


def make_item(code, name, supplier_type, category, unit, item_type="goods", **extra):
    return CatalogItem.objects.create(
        code=code, name_cyr=name, name_lat=name, supplier_type=supplier_type,
        category=category, unit=unit, item_type=item_type, **extra,
    )
