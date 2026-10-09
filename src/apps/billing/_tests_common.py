"""Billing testlari uchun umumiy yordamchilar (fayl nomi `test*` emas — discovery'ga tushmaydi)."""
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.models import (
    ActivityType,
    BillingUserAccess,
    Bolim,
    District,
    LandType,
    PrivilegeType,
    Region,
    Xojalik,
)

User = get_user_model()
BASE = "/api/v1/billing"


def make_user(name: str, role: str, **extra):
    return User.objects.create_user(
        email=f"{name}@example.com", password="TestPassword123!",
        first_name="T", last_name=name.title(), role=role, **extra,
    )


def grant(user, *xojaliklar):
    """billing_user'ga xo'jalik(lar) biriktirish."""
    access, _ = BillingUserAccess.objects.get_or_create(user=user)
    access.xojaliklar.add(*xojaliklar)
    return user


def make_billing_user(name: str, *xojaliklar, **extra):
    return grant(make_user(name, "billing_user", **extra), *xojaliklar)


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@dataclass
class Reference:
    region: Region
    district: District
    xojalik: Xojalik
    bolim: Bolim
    land_type: LandType
    activity_type: ActivityType
    privilege_type: PrivilegeType


def make_reference(code="23:02:06", inn="123456789", name="Test DÒX") -> Reference:
    region, _ = Region.objects.get_or_create(code="1703", defaults={"name": "Андижон вилояти", "billing_id": 2})
    district, _ = District.objects.get_or_create(region=region, code="1703202", defaults={"name": "Андижон тумани"})
    xojalik = Xojalik.objects.create(name=name, region=region, code=code, inn=inn)
    bolim = Bolim.objects.create(name="Markaziy", xojalik=xojalik)
    land_type, _ = LandType.objects.get_or_create(name="Чўл")
    activity_type, _ = ActivityType.objects.get_or_create(name="ўрмон барпо қилиш")
    privilege_type, _ = PrivilegeType.objects.get_or_create(name="Доривор ўсимликлар етиштириш (га) (3 йил)", defaults={"month": 36})
    return Reference(region, district, xojalik, bolim, land_type, activity_type, privilege_type)


def contract_payload(ref: Reference, *, pinfl="12345678901234", contract_number="SH-1", **contract_overrides) -> dict:
    contract = {
        "contract_date": "10.01.2026",
        "contract_number": contract_number,
        "xojalik": str(ref.xojalik.id),
        "bolim": str(ref.bolim.id),
        "region": str(ref.region.id),
        "district": str(ref.district.id),
        "rent_area": "12.50",
        "rent_amount": "1000.00",
        "paid_amount": "400.00",
        "latitude": "40.7000000",
        "longitude": "72.3000000",
    }
    contract.update(contract_overrides)
    return {
        "contract": contract,
        "renter": {"pinfl": pinfl, "full_name": "Test Renter", "phone": "+998901112233", "per_adr": "Andijon"},
        "lands": [{"type": str(ref.land_type.id), "area": "5.00"}],
        "activities": [{"type": str(ref.activity_type.id), "area": "7.50"}],
        "privileges": [{"type": str(ref.privilege_type.id), "area": "1.00"}],
        "action": {"vacancy": "3", "own_investment": "150000.00"},
        "action_products": [{"product_export": "Yong'oq", "product_amount": "10 t", "export_amount": "2000.00"}],
        "yearly_amounts": [
            {"year": 2025, "contract_amount": "500", "calculated_amount": "500", "paid_amount": "200", "penalty_amount": "0"},
            {"year": 2026, "contract_amount": "600", "calculated_amount": "600", "paid_amount": "300", "penalty_amount": "10"},
        ],
    }


def square(lon: float, lat: float, size: float = 0.01) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[[lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size], [lon, lat]]],
    }
