from rest_framework.permissions import BasePermission

class CanCreateReport(BasePermission):
    def has_object_permission(self, request, view, obj=None):
        allowed_roles = ['tashkilot_hodimi', 'hududiy_boshqarma']
        return (
            request.user.role in allowed_roles and
            obj.organization in request.user.organizations.all()
        )
