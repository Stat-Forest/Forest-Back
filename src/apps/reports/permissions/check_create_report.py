from rest_framework.permissions import BasePermission

class CanCreateReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'super_admin':
            return True

        return (
            request.user.role in ['tashkilot_hodimi', 'hududiy_boshqarma']
            and obj.organization == request.user.organization
        )
