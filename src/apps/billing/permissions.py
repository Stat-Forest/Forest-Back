from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.billing.scope import WRITER_ROLES, is_billing_writer  # noqa: F401 — tashqi importlar uchun


class IsBillingWriter(BasePermission):
    """Yozish: billing_user (o'z xo'jaliklari doirasida), billing_super, super_admin yoki superuser."""

    message = "Bu amal faqat Ijara billing foydalanuvchisi uchun ruxsat etilgan."

    def has_permission(self, request, view):
        return is_billing_writer(request.user)


class BillingReadOrWrite(BasePermission):
    """GET/HEAD/OPTIONS — har qanday autentifikatsiyalangan foydalanuvchi; qolgani — IsBillingWriter."""

    message = IsBillingWriter.message

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return is_billing_writer(user)
