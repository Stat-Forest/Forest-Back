from rest_framework.permissions import BasePermission


class CanListReport(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.role in ["tashkilot_hodimi", "hududiy_boshqarma"]
