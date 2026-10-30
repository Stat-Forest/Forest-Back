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

from apps.yashil.schema import YashilAutoSchema
from apps.yashil.services import lang
from apps.yashil.services.scope import CabinetForbidden, is_module_admin, resolve_cabinet

CABINET_HEADER = "HTTP_X_YASHIL_CABINET"
MESSAGE_KEYS = frozenset({"message"})


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
    payload = {"request_id": request_id_for(request), "detail": lang.tr_tree(response.data)}
    if isinstance(exc, YashilError):
        payload.update(error_code=exc.error_code, field=exc.field, message=str(exc.detail))
        if getattr(exc, "index", None) is not None:
            payload["index"] = exc.index
        for key, value in (getattr(exc, "extra", None) or {}).items():
            payload.setdefault(key, lang.tr_tree(value, keys=MESSAGE_KEYS))
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
    payload["message"] = lang.tr(payload["message"])
    return Response(payload, status=response.status_code, headers=response.headers if hasattr(response, "headers") else None)


# ----------------------------------------------------------------------------- idempotency
IDEMPOTENCY_HEADER = "HTTP_IDEMPOTENCY_KEY"


def _request_hash(request) -> str:
    import hashlib, json as _json

    body = request.data if hasattr(request, "data") else {}
    try:
        canonical = _json.dumps(body, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        canonical = str(body)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotentPostMixin:
    """
    POST uchun `Idempotency-Key` (TZ §16.2, §21): bir xil kalit + bir xil body → saqlangan
    javob; boshqa body → 409 `idempotency_mismatch`. `idempotency_required=True` bo'lsa
    kalitsiz so'rov 400. Faqat 2xx/4xx javoblar saqlanadi.
    """

    idempotency_required = True

    def post(self, request, *args, **kwargs):
        from apps.yashil.models import IdempotencyRecord

        key = (request.META.get(IDEMPOTENCY_HEADER) or "").strip()[:128]
        if not key:
            if self.idempotency_required:
                raise YashilError("Idempotency-Key сарлавҳаси мажбурий", error_code="idempotency_key_required",
                                  status_code=status.HTTP_400_BAD_REQUEST)
            return self.perform_post(request, *args, **kwargs)
        path = request.path[:300]
        req_hash = _request_hash(request)
        record = IdempotencyRecord.objects.filter(user=request.user, key=key, path=path).first()
        if record is not None:
            if record.request_hash != req_hash:
                raise YashilError("Бу Idempotency-Key бошқа сўров учун ишлатилган", error_code="idempotency_mismatch",
                                  status_code=status.HTTP_409_CONFLICT)
            return Response(record.response, status=record.status_code)
        response = self.perform_post(request, *args, **kwargs)
        if 200 <= response.status_code < 500 and isinstance(response.data, (dict, list)):
            IdempotencyRecord.objects.get_or_create(
                user=request.user, key=key, path=path,
                defaults={"request_hash": req_hash, "status_code": response.status_code, "response": response.data},
            )
        return response

    def perform_post(self, request, *args, **kwargs):  # pragma: no cover - subclass
        raise NotImplementedError


def service_error(exc) -> YashilError:
    """Servis xatolarini (TransitionError, OrderValidationError, SigningError) API shartnomasiga o'giradi."""
    code = getattr(exc, "code", "business_rule")
    field = getattr(exc, "field", None)
    http = getattr(exc, "status", None)
    if http is None:
        http = status.HTTP_422_UNPROCESSABLE_ENTITY
    err = YashilError(getattr(exc, "message", str(exc)), error_code=code, field=field, status_code=http)
    index = getattr(exc, "index", None)
    if index is not None:
        err.index = index
    err.extra = dict(getattr(exc, "extra", None) or {})
    return err


class CabinetMixin:
    """`self.cabinet` (YashilMembership | None) va `self.is_admin` ni so'rov boshida aniqlaydi."""

    cabinet = None
    is_admin = False
    schema = YashilAutoSchema()

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
    "CABINET_HEADER", "CabinetMixin", "IdempotentPostMixin", "service_error", "CanPrepare", "CanSign", "HasCabinet", "IsAuthenticated", "IsModuleAdmin",
    "YashilError", "invalid_format", "not_found", "request_id_for", "yashil_exception_handler",
]
