from rest_framework.permissions import BasePermission
from apps.users.models.users import CustomUser


class CanCancelReport(BasePermission):
    """
    Report cancel qilish permissioni:

    - tashkilot_rahbari:
        status in ['saved', 'sent']
        va user.organization == obj.created_by.organization

    - hududiy_boshqarma:
        status == 'sent'
        va obj.organization user.region_user_orgs ichida

    - bolim_admin:
        status == 'sent'
        va obj.statement_parent == user.statement
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = user.role

        # 1️⃣ Tashkilot rahbari
        if role == CustomUser.Role.TASHKILOT_RAHBARI:
            return (
                obj.status in ["saved", "sent"]
                and user.organization_id == obj.created_by.organization_id
            )

        # 2️⃣ Hududiy boshqarma
        if role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            return (
                obj.status == "sent"
                and obj.organization_id in user.region_user_orgs.values_list("id", flat=True)
            )

        # 3️⃣ Bo‘lim admin
        if role == CustomUser.Role.BOLIM_ADMIN:
            return (
                obj.status == "sent"
                and obj.statement_parent_id == user.statement_id
            )

        return False
