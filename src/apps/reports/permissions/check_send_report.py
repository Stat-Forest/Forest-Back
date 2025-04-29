from rest_framework.permissions import BasePermission


class CanSendReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.role == 'tashkilot_rahbari' and
            obj.status == 'saved'
        )