from rest_framework.permissions import BasePermission
from apps.users.models import CustomUser


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
