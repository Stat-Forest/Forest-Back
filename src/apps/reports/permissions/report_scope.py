from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.reports.permissions.check_send_report import _get_effective_status
from apps.users.models import CustomUser

# Barcha hisobotlarni ko'ra oladigan rollar
FULL_ACCESS_ROLES = {
    CustomUser.Role.SUPER_ADMIN,
    CustomUser.Role.RAHBARIYAT,
}

# Hisobot ma'lumotlarini tahrirlay oladigan rollar
EDITOR_ROLES = {
    CustomUser.Role.TASHKILOT_HODIMI,
    CustomUser.Role.HUDUDIY_BOSHQARMA,
}

EDITABLE_STATUSES = {"saved", "cancelled"}


def scope_reports_for_billing_role(queryset, user):
    """
    Ijara billing rollari (billing_user/billing_super): faqat "O'rmon kadastri va
    monitoringi" bo'limi hisobotlari; tashkilot: billing_super — hammasi,
    billing_user — o'z tashkiloti ∪ biriktirilgan xo'jaliklar tashkilotlari.
    """
    from apps.billing.scope import billing_organization_ids
    from apps.reports.services.kadastr import get_kadastr_parent_id

    kadastr_id = get_kadastr_parent_id()
    if not kadastr_id:
        return queryset.none()
    queryset = queryset.filter(statement__parent_id=kadastr_id)
    org_ids = billing_organization_ids(user)
    if org_ids is None:
        return queryset
    if not org_ids:
        return queryset.none()
    return queryset.filter(organization_id__in=org_ids)


def scope_reports_for_user(queryset, user):
    """
    Report querysetini foydalanuvchi roliga qarab cheklaydi
    (ReportListAPIView dagi qoidalar bilan bir xil):

    - superuser / super_admin / rahbariyat -> hammasi
    - tashkilot_hodimi / tashkilot_rahbari -> faqat o'z tashkiloti
    - bolim_admin -> faqat o'z bo'limi (statement.parent)
    - hududiy_boshqarma -> faqat biriktirilgan tashkilotlar hududi
    - billing_user / billing_super -> kadastr bo'limi (scope_reports_for_billing_role)
    - boshqalar -> hech narsa
    """
    if not user or not user.is_authenticated:
        return queryset.none()

    if user.is_superuser or user.role in FULL_ACCESS_ROLES:
        return queryset

    if user.role in (CustomUser.Role.BILLING_USER, CustomUser.Role.BILLING_SUPER):
        return scope_reports_for_billing_role(queryset, user)

    if user.role in (CustomUser.Role.TASHKILOT_HODIMI, CustomUser.Role.TASHKILOT_RAHBARI):
        if not user.organization_id:
            return queryset.none()
        return queryset.filter(organization_id=user.organization_id)

    if user.role == CustomUser.Role.BOLIM_ADMIN:
        if not user.statement_id:
            return queryset.none()
        return queryset.filter(statement__parent_id=user.statement_id)

    if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
        regions = list(
            user.region_user_orgs.values_list("region", flat=True).distinct()
        )
        if not regions:
            return queryset.none()
        return queryset.filter(organization__region__in=regions)

    return queryset.none()


def scope_plans_for_user(queryset, user):
    """
    Plan querysetini rol bo'yicha cheklaydi (hisobotlar bilan bir xil qoida):
    super_admin/rahbariyat -> hammasi; bolim_admin -> o'z bo'limi
    (statement.parent); tashkilot_* -> o'z tashkiloti; hududiy -> hududi.
    """
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.is_superuser or user.role in FULL_ACCESS_ROLES:
        return queryset
    if user.role == CustomUser.Role.BOLIM_ADMIN:
        if not user.statement_id:
            return queryset.none()
        return queryset.filter(statement__parent_id=user.statement_id)
    if user.role in (CustomUser.Role.TASHKILOT_HODIMI, CustomUser.Role.TASHKILOT_RAHBARI):
        if not user.organization_id:
            return queryset.none()
        return queryset.filter(organization_id=user.organization_id)
    if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
        regions = list(user.region_user_orgs.values_list("region", flat=True).distinct())
        if not regions:
            return queryset.none()
        return queryset.filter(organization__region__in=regions)
    return queryset.none()


def scope_regional_reports_for_user(queryset, user):
    """
    Viloyat yig'ma hisobotlari (is_general): tashkilot xodimi/rahbari faqat
    o'z viloyatini, hududiy boshqarma — biriktirilgan hududlarni, markaziy
    rollar — hammasini ko'radi.
    """
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.is_superuser or user.role in FULL_ACCESS_ROLES or user.role == CustomUser.Role.BOLIM_ADMIN:
        return queryset
    if user.role in (CustomUser.Role.TASHKILOT_HODIMI, CustomUser.Role.TASHKILOT_RAHBARI):
        region = getattr(user.organization, "region", None) if user.organization_id else None
        return queryset.filter(region=region) if region else queryset.none()
    if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
        regions = list(user.region_user_orgs.values_list("region", flat=True).distinct())
        return queryset.filter(region__in=regions) if regions else queryset.none()
    return queryset.none()


class PlanScopedQuerysetMixin:
    """Plan view'lari uchun: ruxsatsiz reja 404 qaytaradi."""

    def get_queryset(self):
        return scope_plans_for_user(super().get_queryset(), self.request.user)


class ReportScopedQuerysetMixin:
    """
    View querysetini scope_reports_for_user orqali cheklaydi.
    Ruxsatsiz hisobot 404 qaytaradi (mavjudligi oshkor qilinmaydi).
    """

    def get_queryset(self):
        return scope_reports_for_user(super().get_queryset(), self.request.user)


class CanEditReportData(BasePermission):
    """
    Hisobot ma'lumotlarini o'zgartirish: faqat EDITOR_ROLES va faqat
    hisobot saved/cancelled holatida bo'lsa. O'qish (GET) uchun
    cheklov querysetdagi scope orqali qo'llanadi.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(
            user and user.is_authenticated
            and (user.is_superuser or user.role in EDITOR_ROLES)
        )

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return _get_effective_status(obj) in EDITABLE_STATUSES
