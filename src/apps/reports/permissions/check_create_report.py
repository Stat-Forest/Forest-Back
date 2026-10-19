from rest_framework.permissions import BasePermission

CREATE_ROLES = ("super_admin", "tashkilot_hodimi")


class CanCreateReport(BasePermission):
    """Hisobotni faqat tashkilot hodimi (va super_admin) yaratadi.

    DRF create'da has_object_permission chaqirilmaydi — rol tekshiruvi
    has_permission'da bo'lishi shart (audit B12).
    """

    message = "Hisobot yaratish faqat tashkilot hodimi uchun."

    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in CREATE_ROLES

    def has_object_permission(self, request, view, obj):
        if request.user.role == "super_admin":
            return True
        return (
            request.user.role in ["tashkilot_hodimi"]
            and obj.organization == request.user.organization
        )
