from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.users.models import CustomUser

WRITER_ROLES = {CustomUser.Role.BILLING_USER, CustomUser.Role.SUPER_ADMIN}


def is_billing_writer(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (user.role in WRITER_ROLES or user.is_superuser)
    )


class IsBillingWriter(BasePermission):
    """Yozish: faqat billing_user yoki super_admin (is_superuser)."""

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
