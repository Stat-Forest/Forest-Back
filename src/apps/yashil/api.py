"""
Modul API asosi: xato shartnomasi (TZ §21) va kabinet aniqlash.

Javob (xato): {"error_code", "field", "message", "request_id", "detail"?}
Kabinet: `X-Yashil-Cabinet: <membership uuid>` header'i; bo'lmasa birinchi faol a'zolik.
"""
import uuid

from rest_framework import status
from rest_framework.exceptions import APIException, NotAuthenticated, PermissionDenied, Throttled, ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.yashil.services.scope import CabinetForbidden, is_module_admin, resolve_cabinet

CABINET_HEADER = "HTTP_X_YASHIL_CABINET"


class YashilError(APIException):
    """Biznes qoidasi yoki format xatosi — error_code/field bilan."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "business_rule"

    def __init__(self, message, *, error_code=None, field=None, status_code=None):
        super().__init__(detail=message, code=error_code or self.default_code)
        self.error_code = error_code or self.default_code
        self.field = field
        if status_code is not None:
            self.status_code = status_code


def invalid_format(message, field):
    return YashilError(message, error_code="invalid_format", field=field, status_code=status.HTTP_400_BAD_REQUEST)


def not_found(message="Обект топилмади ёки очиш ҳуқуқи йўқ"):
    return YashilError(message, error_code="not_found", status_code=status.HTTP_404_NOT_FOUND)


def request_id_for(request) -> str:
    rid = request.META.get("HTTP_X_REQUEST_ID") if request is not None else None
    return (rid or uuid.uuid4().hex)[:32]


def _first_message(detail):
    if isinstance(detail, dict):
        for value in detail.values():
            return _first_message(value)
    if isinstance(detail, (list, tuple)) and detail:
        return _first_message(detail[0])
    return str(detail)


def yashil_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    request = context.get("request")
    payload = {"request_id": request_id_for(request), "detail": response.data}
    if isinstance(exc, YashilError):
        payload.update(error_code=exc.error_code, field=exc.field, message=str(exc.detail))
    elif isinstance(exc, ValidationError):
        field = next(iter(exc.detail), None) if isinstance(exc.detail, dict) else None
        payload.update(error_code="validation", field=field, message=_first_message(exc.detail))
    elif isinstance(exc, NotAuthenticated):
        payload.update(error_code="unauthenticated", field=None, message=_first_message(response.data))
    elif isinstance(exc, PermissionDenied):
        code = getattr(exc, "default_code", "forbidden")
        detail_code = getattr(exc.detail, "code", None)
        payload.update(error_code=detail_code or code, field=None, message=_first_message(response.data))
    elif isinstance(exc, Throttled):
        payload.update(error_code="rate_limited", field=None, message=_first_message(response.data))
    else:
        payload.update(error_code=getattr(exc, "default_code", "error"), field=None, message=_first_message(response.data))
    return Response(payload, status=response.status_code, headers=response.headers if hasattr(response, "headers") else None)


class CabinetMixin:
    """`self.cabinet` (YashilMembership | None) va `self.is_admin` ni so'rov boshida aniqlaydi."""

    cabinet = None
    is_admin = False

    def get_exception_handler(self):
        return yashil_exception_handler

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.is_admin = is_module_admin(request.user)
        try:
            self.cabinet = resolve_cabinet(request.user, request.META.get(CABINET_HEADER))
        except CabinetForbidden:
            raise PermissionDenied("Бу кабинет сизга тегишли эмас.", code="cabinet_forbidden")
        self.check_cabinet_permissions(request)

    def check_cabinet_permissions(self, request):
        for permission in getattr(self, "cabinet_permission_classes", ()):
            if not permission().has_cabinet_permission(request, self):
                raise PermissionDenied(getattr(permission, "message", "Рухсат йўқ"), code=getattr(permission, "code", "forbidden"))


class HasCabinet(BasePermission):
    """Faol a'zolik yoki modul admini bo'lishi shart."""

    message = "Сиз «Яшил маҳалла» модулига бириктирилмагансиз."
    code = "not_member"

    def has_cabinet_permission(self, request, view):
        return view.is_admin or view.cabinet is not None


class CanPrepare(BasePermission):
    message = "Бу кабинетда ҳужжат тайёрлаш ҳуқуқи йўқ."
    code = "cannot_prepare"

    def has_cabinet_permission(self, request, view):
        return view.cabinet is not None and view.cabinet.can_prepare


class CanSign(BasePermission):
    message = "Бу кабинетда имзолаш ҳуқуқи йўқ."
    code = "cannot_sign"

    def has_cabinet_permission(self, request, view):
        return view.cabinet is not None and view.cabinet.can_sign


class IsModuleAdmin(BasePermission):
    message = "Фақат модул администратори учун."
    code = "admin_only"

    def has_cabinet_permission(self, request, view):
        return view.is_admin


__all__ = [
    "CABINET_HEADER", "CabinetMixin", "CanPrepare", "CanSign", "HasCabinet", "IsAuthenticated", "IsModuleAdmin",
    "YashilError", "invalid_format", "not_found", "request_id_for", "yashil_exception_handler",
]
