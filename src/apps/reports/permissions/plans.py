from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission
from apps.users.models import CustomUser


class IsBolimAdmin(BasePermission):
    """
    Faqat bo'lim adminlari uchun ruxsat (Plan Excel template / import / export).

    `has_permission` view darajasida ishlaydi — APIView'larda ham (obj bo'lmasa
    ham) chaqiriladi, shuning uchun `CanCreatePlan` (faqat has_object_permission)
    dan farqli o'laroq template/import kabi GET/POST'larni ishonchli cheklaydi.
    """
    message = _("Bu amal faqat bo'lim adminlari uchun ruxsat etilgan.")

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == CustomUser.Role.BOLIM_ADMIN
        )


class CanManagePlan(BasePermission):
    """
    Plan CREATE / UPDATE / DELETE permission
    """

    allowed_roles = {
        CustomUser.Role.BOLIM_ADMIN,
    }

    def has_permission(self, request, view):
        # CREATE paytida ishlaydi (obj yo‘q)
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return False

        return (
            request.user.is_authenticated and
            request.user.role in self.allowed_roles
        )

    def has_object_permission(self, request, view, obj):
        # UPDATE / DELETE paytida ishlaydi
        if request.user.role not in self.allowed_roles:
            return False

        # user.statement bo‘lishi shart
        if not request.user.statement:
            return False

        # Plan.statement.parent === user.statement
        return obj.statement.parent_id == request.user.statement_id
