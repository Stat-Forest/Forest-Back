from rest_framework.permissions import BasePermission


class CanAcceptReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.role == 'bolim_admin' and
            obj.status == 'sent'
        )