"""
Statdagi o'rmon xo'jaliklarini yetkazib beruvchi qilish.

Platformadagi `general.Organization` lar orasidan nomida «o'rmon» / «ўрмон» bo'lgan,
viloyatga tegishli (respublika tashkilotlari emas) va hali profili yo'q tashkilotlarga
`SupplierProfile(forest)` ochiladi. Takror ishga tushirish xavfsiz — mavjud profillar o'zgarmaydi.
"""
from django.db import transaction
from django.db.models import Q

from apps.general.models import Organization
from apps.utils.services import RegionChoices
from apps.yashil.models import SupplierProfile

# o'rmon / o‘rmon / oʻrmon / ўрмон (icontains katta-kichik harfni farqlamaydi)
FOREST_NAME_Q = Q(name__iregex=r"o.?rmon") | Q(name__icontains="ўрмон")


def forest_candidates():
    return (Organization.objects.filter(FOREST_NAME_Q, supplier_profile__isnull=True)
            .exclude(region=RegionChoices.REPUBLIC).order_by("region", "name"))


@transaction.atomic
def sync_forests(organization_ids=None, user=None) -> list[SupplierProfile]:
    qs = forest_candidates()
    if organization_ids is not None:
        qs = qs.filter(pk__in=organization_ids)
    created = []
    for org in qs:
        profile = SupplierProfile(organization=org, supplier_type=SupplierProfile.SupplierType.FOREST,
                                  stir=str(org.stir or "")[:9])
        if user is not None:
            profile._history_user = user
        profile.save()
        created.append(profile)
    return created
