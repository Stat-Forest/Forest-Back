from rest_framework.permissions import BasePermission

from apps.reports.permissions.check_send_report import _get_effective_status
from apps.users.models import CustomUser


class CanAcceptReport(BasePermission):
    """
    Hisobotni qabul qilish permissioni.

    Faqat bolim_admin qabul qila oladi.

    Daromad uchun:
        current_quarter status == 'sent' bo'lishi shart.

    Oddiy report uchun:
        report.status == 'sent' bo'lishi shart.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == CustomUser.Role.BOLIM_ADMIN
        )

    def has_object_permission(self, request, view, obj):
        if request.user.role != CustomUser.Role.BOLIM_ADMIN:
            return False

        effective_status = _get_effective_status(obj)
        return effective_status == "sent"

# from rest_framework.permissions import BasePermission
#
#
# class CanAcceptReport(BasePermission):
#     def has_object_permission(self, request, view, obj):
#         return (
#             request.user.role == 'bolim_admin' and
#             obj.status == 'sent'
#         )