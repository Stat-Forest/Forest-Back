from rest_framework.permissions import BasePermission

from apps.users.models.users import CustomUser
from apps.reports.services.quarter_validator import DaromadQuarterService


def _get_effective_status(obj) -> str:
    """
    Report'ning effektiv statusini qaytaradi.

    Daromad uchun: current_quarter ning statusini qaytaradi.
    Oddiy report uchun: report.status ni qaytaradi.

    Bu funksiya permission qatlamida report.status ga to'g'ridan-to'g'ri
    murojaat qilishni oldini oladi — Daromadda report.status har doim
    ACCEPTED bo'lib turadi (Q1 qabul qilingan bo'lsa), lekin current_quarter
    SAVED yoki SENT bo'lishi mumkin.
    """
    if DaromadQuarterService.is_daromad_report(obj):
        current_quarter = getattr(obj, "current_quarter", None)
        if not current_quarter:
            return ""
        return obj.get_quarter_status(current_quarter) or ""
    return obj.status or ""


class CanSendReport(BasePermission):
    """
    Hisobotni jo'natish permissioni.

    Faqat tashkilot_rahbari jo'nata oladi.

    Daromad uchun:
        current_quarter status == 'saved' bo'lishi shart.
        (report.status ACCEPTED bo'lsa ham, current_quarter SAVED bo'lishi mumkin)

    Oddiy report uchun:
        report.status == 'saved' bo'lishi shart.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == CustomUser.Role.TASHKILOT_RAHBARI
        )

    def has_object_permission(self, request, view, obj):
        if request.user.role != CustomUser.Role.TASHKILOT_RAHBARI:
            return False

        effective_status = _get_effective_status(obj)
        return effective_status == "saved"

# from rest_framework.permissions import BasePermission
# from apps.reports.services.quarter_validator import DaromadQuarterService
#
#
# class CanSendReport(BasePermission):
#     def has_object_permission(self, request, view, obj):
#         if request.user.role != 'tashkilot_rahbari':
#             return False
#
#         if DaromadQuarterService.is_daromad_report(obj):
#             # Daromad: current_quarter ning statusini tekshiramiz
#             current_quarter = obj.current_quarter
#             if not current_quarter:
#                 return False
#             return obj.get_quarter_status(current_quarter) == 'saved'
#
#         # Oddiy report
#         return obj.status == 'saved'