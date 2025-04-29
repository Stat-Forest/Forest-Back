from rest_framework.permissions import BasePermission


class CanUpdateReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            obj.status in ['saved', 'cancelled']
            and request.user.role in ['tashkilot_hodimi', 'hududiy_boshqarma']
            and
            request.user == obj.created_by
        )