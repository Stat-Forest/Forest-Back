from rest_framework.permissions import BasePermission


class CanCreatePlan(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.role == 'bolim_admin'
        )