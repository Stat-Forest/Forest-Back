from rest_framework import permissions


class IsInGroup(permissions.BasePermission):
    group_name = None

    def has_permission(self, request, view):
        if not self.group_name:
            return False
        return request.user.groups.filter(name=self.group_name).exists()


class IsSuperUser(IsInGroup):
    group_name = "SuperUser"


class IsRahbariyat(IsInGroup):
    group_name = "Rahbariyat"


class IsBolimAdmin(IsInGroup):
    group_name = "BolimAdmin"


class IsTashkilotRahbari(IsInGroup):
    group_name = "TashkilotRahbari"


class IsTashkilothodimlari(IsInGroup):
    group_name = "TashkilotHodimlari"