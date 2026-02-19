from rest_framework.permissions import BasePermission


class CanDeleteReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'super_admin':
            return True

        return (
            obj.status in ['saved', 'cancelled']
            and request.user.role in ['tashkilot_hodimi', 'hududiy_boshqarma']
            and request.user == obj.created_by
        )