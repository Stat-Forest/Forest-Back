from rest_framework.permissions import BasePermission

from apps.reports.permissions.check_send_report import _get_effective_status
from apps.users.models import CustomUser


class CanCancelReport(BasePermission):
    """
    Hisobotni bekor qilish permissioni.

    Daromad uchun current_quarter statusiga qaraladi,
    oddiy report uchun report.status ga qaraladi.

    Qoidalar:
    - tashkilot_rahbari:
        * effective_status in ['saved', 'sent']
        * va user.organization == obj.organization (created_by orqali emas)
    - hududiy_boshqarma:
        * effective_status == 'sent'
        * va obj.organization user.region_user_orgs ichida
    - bolim_admin:
        * effective_status == 'sent'
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (
                CustomUser.Role.TASHKILOT_RAHBARI,
                CustomUser.Role.HUDUDIY_BOSHQARMA,
                CustomUser.Role.BOLIM_ADMIN,
            )
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = user.role
        effective_status = _get_effective_status(obj)

        if role == CustomUser.Role.TASHKILOT_RAHBARI:
            if effective_status not in ("saved", "sent"):
                return False
            # Faqat o'z tashkilotining hisobotini bekor qila oladi
            return user.organization_id == obj.organization_id

        if role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            if effective_status != "sent":
                return False
            org_ids = set(
                user.region_user_orgs.values_list("id", flat=True)
            )
            return obj.organization_id in org_ids

        if role == CustomUser.Role.BOLIM_ADMIN:
            return effective_status == "sent"

        return False

# from rest_framework.permissions import BasePermission
# from apps.users.models.users import CustomUser
#
#
# class CanCancelReport(BasePermission):
#     """
#     Report cancel qilish permissioni:
#
#     - tashkilot_rahbari:
#         status in ['saved', 'sent']
#         va user.organization == obj.created_by.organization
#
#     - hududiy_boshqarma:
#         status == 'sent'
#         va obj.organization user.region_user_orgs ichida
#
#     - bolim_admin:
#         status == 'sent'
#         va obj.statement_parent == user.statement
#     """
#
#     def has_object_permission(self, request, view, obj):
#         user = request.user
#         role = user.role
#
#         # 1️⃣ Tashkilot rahbari
#         if role == CustomUser.Role.TASHKILOT_RAHBARI:
#             return (
#                 obj.status in ["saved", "sent"]
#                 and user.organization_id == obj.created_by.organization_id
#             )
#
#         # 2️⃣ Hududiy boshqarma
#         if role == CustomUser.Role.HUDUDIY_BOSHQARMA:
#             return (
#                 obj.status == "sent"
#                 and obj.organization_id in user.region_user_orgs.values_list("id", flat=True)
#             )
#
#         # 3️⃣ Bo‘lim admin
#         if role == CustomUser.Role.BOLIM_ADMIN:
#             return obj.status == "sent"
#
#         return False
