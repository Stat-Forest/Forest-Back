from rest_framework.permissions import BasePermission


class CanCancelReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.role in ['tashkilot_rahbari', 'bolim_admin'] and
            obj.status in ['saved', 'sent','accepted']
        )
