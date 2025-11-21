from rest_framework.permissions import BasePermission


class CanDeleteReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        print("📌 Report status:", obj.status)
        print("📌 Report created_by:", obj.created_by)
        print("📌 Current user:", request.user)
        print("📌 Current user role:", request.user.role)
        if request.user.role == 'super_admin':
            return True

        return (
            obj.status in ['saved', 'cancelled']
            and request.user.role in ['tashkilot_hodimi', 'hududiy_boshqarma']
            and request.user == obj.created_by
        )