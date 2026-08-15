from rest_framework import permissions

from apps.users.models import CustomUser


def is_support_admin(user) -> bool:
    """
    Support admin — chat navbatini yurituvchi rol.
    """

    return getattr(user, "role", None) == CustomUser.Role.SUPPORT_ADMIN


def is_chat_supervisor(user) -> bool:
    """
    Super admin — biriktirilishidan qat'i nazar istalgan chatni
    majburan yopa oladigan nazoratchi.
    """

    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "role", None) == CustomUser.Role.SUPER_ADMIN
    )


def can_manage_support_chat(user) -> bool:
    """
    Chatni olish/yopish huquqi.

    MUHIM: bu yerda ataylab `has_perm("chat.manage_support_chat")`
    ishlatilmaydi. O'sha ruxsat hech qachon hech kimga berilmagan
    (`apps/users/create_role_users.py` dagi guruh-ruxsat jadvalida
    `support_admin` umuman yo'q), shuning uchun eski tekshiruv
    haqiqiy support adminlarni ham to'sib qo'yardi.
    """

    if not getattr(user, "is_authenticated", False):
        return False

    return is_support_admin(user) or is_chat_supervisor(user)


class IsSupportAdmin(permissions.BasePermission):
    """
    Faqat support admin (yoki super admin) uchun ochiq endpointlar.
    """

    message = "Support administrator permissions required."

    def has_permission(self, request, view) -> bool:
        return can_manage_support_chat(request.user)
