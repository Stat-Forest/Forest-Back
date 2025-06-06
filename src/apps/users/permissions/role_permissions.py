from rest_framework import permissions


class IsInGroup(permissions.BasePermission):
    groups = []

    def has_permission(self, request, view):
        return request.user.groups.filter(name__in=self.groups).exists()


class IsSuperUser(IsInGroup):
    groups = ["SuperUser"]


class IsRahbariyat(IsInGroup):
    groups = ["Rahbariyat"]


class IsBolimAdmin(IsInGroup):
    groups = ["BolimAdmin"]


class IsTashkilotRahbari(IsInGroup):
    groups = ["TashkilotRahbari"]


class IsTashkilothodimlari(IsInGroup):
    groups = ["TashkilotHodimlari"]