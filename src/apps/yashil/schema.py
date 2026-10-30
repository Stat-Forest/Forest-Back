"""
Modul view'lari uchun drf-spectacular sxema klassi (`CabinetMixin.schema`).

Amallar tavsifi `apps.yashil.openapi.OPERATIONS` da; bu yerda faqat umumiy qismlar — teg, operationId,
kabinet va `Idempotency-Key` header'lari, xato javoblari. `openapi` moduli serializer'larni import qiladi,
ular esa `api` ni — shuning uchun u kechiktirib import qilinadi.
"""
from drf_spectacular.drainage import error
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers

API_PREFIX = "/api/v1/yashil/"
PUBLIC_VIEWS = {"PublicVerifyView"}


class YashilErrorSerializer(serializers.Serializer):
    """Xato javobi (TZ §21): error_code, field, o'zbekcha message, request_id."""

    error_code = serializers.CharField(help_text="Машина ўқийдиган код: validation, forbidden, not_found, version_conflict, state_conflict, …")
    field = serializers.CharField(allow_null=True, help_text="Хатога сабаб бўлган майдон (бўлса)")
    message = serializers.CharField(help_text="Фойдаланувчига кўрсатиладиган ўзбекча матн")
    request_id = serializers.CharField(help_text="So'rov identifikatori (X-Request-ID ёки сервер берган)")
    detail = serializers.JSONField(required=False, help_text="DRF асл тафсилоти")



TAGS = {
    "orders": "Буюртмалар", "cancel": "Бекор қилиш", "acts": "Далолатномалар", "stock": "Омбор",
    "admin": "Маъмурий созламалар", "reports": "Ҳисоботлар", "stats": "Статистика ва харита", "map": "Статистика ва харита",
    "documents": "Ҳужжатлар ва QR", "verify": "Ҳужжатлар ва QR", "notifications": "Хабарномалар",
}
DEFAULT_TAG = "Маълумотномалар"


class YashilAutoSchema(AutoSchema):
    """`OPERATIONS` dan o'qiydi; header'lar va xato javoblarini qo'shadi."""

    @property
    def _key(self):
        return f"{self.view.__class__.__name__}.{self.method.lower()}"

    @property
    def _op(self):
        from apps.yashil.openapi import OPERATIONS, Op

        op = OPERATIONS.get(self._key)
        if op is None:
            error(f"{self._key}: OPERATIONS da tavsif yo'q")
            return Op(self._key)
        return op

    @property
    def _public(self):
        return self.view.__class__.__name__ in PUBLIC_VIEWS

    def _segments(self):
        return [s for s in self.path.removeprefix(API_PREFIX).strip("/").split("/") if s]

    def get_operation_id(self):
        segs = self._segments()
        words = [s.replace("-", "_") for s in segs if not s.startswith("{")]
        if segs and segs[-1].startswith("{"):
            words.append("item")
        return "_".join(["yashil", *words, self.method.lower()])

    def get_tags(self):
        segs = self._segments()
        return [TAGS.get(segs[0] if segs else "", DEFAULT_TAG)]

    def get_summary(self):
        return self._op.summary

    def get_description(self):
        return self._op.description or None

    def get_auth(self):
        return [{}] if self._public else super().get_auth()

    def get_override_parameters(self):
        from apps.yashil.api import IdempotentPostMixin

        params = list(self._op.params)
        if not self._public:
            params.append(OpenApiParameter(
                "X-Yashil-Cabinet", OpenApiTypes.UUID, OpenApiParameter.HEADER, required=False,
                description="Фаол кабинет (аъзолик ID). Бўлмаса — биринчи фаол аъзолик."))
        if self.method == "POST" and isinstance(self.view, IdempotentPostMixin):
            params.append(OpenApiParameter(
                "Idempotency-Key", str, OpenApiParameter.HEADER, required=getattr(self.view, "idempotency_required", True),
                description="Такрор сўров идентификатори: бир хил калит ва мазмун — сақланган жавоб, бошқа мазмун — 409."))
        return params

    def get_request_serializer(self):
        op = self._op
        if op.request is None:
            return None
        return {"multipart/form-data": op.request} if op.multipart else op.request

    def get_response_serializers(self):
        op = self._op
        responses = {op.status: op.response}
        errors = []
        writes = self.method in ("POST", "PUT", "PATCH")
        if writes or op.params:
            errors.append(400)
        if not self._public:
            errors += [401, 403]
        if "{" in self.path or not self._public:
            errors.append(404)
        if writes:
            errors += [409, 422]
        errors.append(429)
        for code in errors:
            responses[code] = YashilErrorSerializer
        return responses
