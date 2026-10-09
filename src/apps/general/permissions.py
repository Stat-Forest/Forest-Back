from apps.users.models import CustomUser

# Barcha tashkilotlarning ma'lumotini ko'radigan rollar
ALL_ORGANIZATIONS_ROLES = {
    CustomUser.Role.SUPER_ADMIN,
    CustomUser.Role.RAHBARIYAT,
    CustomUser.Role.BOLIM_ADMIN,
}
ORGANIZATION_ROLES = {
    CustomUser.Role.TASHKILOT_HODIMI,
    CustomUser.Role.TASHKILOT_RAHBARI,
}
# Ijara billing rollari — kadastr bo'limidagi yer hujjatlarini o'qiydi (faqat o'qish)
BILLING_ROLES = {
    CustomUser.Role.BILLING_USER,
    CustomUser.Role.BILLING_SUPER,
}


def scope_by_organization(queryset, user, org_field: str = "organization"):
    """
    Tashkilotga bog'langan yozuvlarni (yer hujjatlari va h.k.) rol bo'yicha cheklaydi:
    - super_admin / rahbariyat / bolim_admin -> hammasi
    - tashkilot_hodimi / tashkilot_rahbari -> faqat o'z tashkiloti
    - hududiy_boshqarma -> biriktirilgan tashkilotlar hududi
    - billing_super -> hammasi; billing_user -> o'z tashkiloti va xo'jaliklari tashkilotlari
    - boshqalar -> hech narsa
    """
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.is_superuser or user.role in ALL_ORGANIZATIONS_ROLES:
        return queryset
    if user.role in ORGANIZATION_ROLES:
        if not user.organization_id:
            return queryset.none()
        return queryset.filter(**{f"{org_field}_id": user.organization_id})
    if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
        regions = list(user.region_user_orgs.values_list("region", flat=True).distinct())
        if not regions:
            return queryset.none()
        return queryset.filter(**{f"{org_field}__region__in": regions})
    if user.role in BILLING_ROLES:
        # billing_super -> hammasi; billing_user -> o'z tashkiloti ∪ xo'jaliklari tashkilotlari
        from apps.billing.scope import billing_organization_ids

        org_ids = billing_organization_ids(user)
        if org_ids is None:
            return queryset
        if not org_ids:
            return queryset.none()
        return queryset.filter(**{f"{org_field}_id__in": org_ids})
    return queryset.none()


def allowed_organization_for_create(user, organization):
    """
    Yozuv yaratishda tashkilotni aniqlaydi. Tashkilot xodimi/rahbari uchun
    har doim o'z tashkiloti (yuborilgani e'tiborga olinmaydi); hududiy
    boshqarma faqat o'z hududidagi tashkilot nomidan; qolganlar — istalgan.
    None qaytsa — ruxsat yo'q.
    """
    if user.is_superuser or user.role in ALL_ORGANIZATIONS_ROLES:
        return organization
    if user.role in ORGANIZATION_ROLES:
        return user.organization
    if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA and organization is not None:
        regions = set(user.region_user_orgs.values_list("region", flat=True))
        return organization if organization.region in regions else None
    return None
