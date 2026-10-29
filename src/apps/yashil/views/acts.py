"""Dalolatnoma API (TZ §10, §12, §14, §21): yaratish, tahrir/versiya, ilovalar, ikki imzo, qaytarish, bekor, reestr."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Prefetch, Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.pagination import CustomPageNumberPagination
from apps.yashil.api import CabinetMixin, HasCabinet, IdempotentPostMixin, IsAuthenticated, YashilError, not_found, service_error
from apps.yashil.models import ATTACHMENT_TOTAL_MAX, Act, ActAttachment, ActLine, ActVersion, DocumentVersion, YashilMembership
from apps.yashil.serializers_acts import (
    ActAttachmentSerializer,
    ActCancelSerializer,
    ActDetailSerializer,
    ActListSerializer,
    ActReturnSerializer,
    ActSignSerializer,
    ActWriteSerializer,
)
from apps.yashil.services import acts as act_service
from apps.yashil.services.signing import SigningError
from apps.yashil.services.transitions import TransitionError
from apps.yashil.services.scope import acts_for_cabinet  # noqa: F401 — cancel/documents view'lari shu nomdan foydalanadi
from apps.yashil.views.orders import OrderBaseView

T = YashilMembership.MemberType


def act_detail_queryset(qs):
    lines = ActLine.objects.select_related("order_line__catalog_item")
    return qs.prefetch_related(
        Prefetch("current_version__lines", queryset=lines),
        Prefetch("versions", queryset=ActVersion.objects.prefetch_related(Prefetch("lines", queryset=lines))),
        "attachments",
        Prefetch("document__versions", queryset=DocumentVersion.objects.prefetch_related("signatures")),
        "document__current_version__signatures",
    )


class ActBaseView(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (HasCabinet,)

    def get_act(self, act_id) -> Act:
        act = acts_for_cabinet(self.cabinet, self.is_admin).filter(pk=act_id).first()
        if act is None:
            raise not_found("Далолатнома топилмади ёки очиш ҳуқуқи йўқ")
        return act

    def detail(self, act, http_status=status.HTTP_200_OK):
        act = act_detail_queryset(acts_for_cabinet(self.cabinet, self.is_admin)).get(pk=act.pk)
        return Response(ActDetailSerializer(act, context={"request": self.request, "cabinet": self.cabinet}).data, status=http_status)

    def require_supplier_prepare(self, act):
        cab = self.cabinet
        if cab is None or cab.member_type != T.SUPPLIER or act.order.supplier_org_id != cab.organization_id or not cab.can_prepare:
            raise YashilError("Далолатномани фақат етказиб берувчи кабинети тайёрлайди", error_code="forbidden", status_code=403)
        if act.status not in (Act.Status.DRAFT, Act.Status.RETURNED):
            raise YashilError("Далолатнома бу ҳолатда таҳрирланмайди", error_code="state_conflict", status_code=409)


def _lines(data):
    return [{"order_line": l["order_line"], "qty": l["qty"]} for l in data.get("lines") or []]


class OrderActsCreateView(IdempotentPostMixin, OrderBaseView):
    """`POST orders/{id}/acts/` — yetkazishni qayd etish va akt qoralamasi (TZ §10.1)."""

    def perform_post(self, request, order_id):
        order = self.get_order(order_id)
        ser = ActWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            act = act_service.create_act(order, self.cabinet, delivery_date=d["delivery_date"], lines=_lines(d), responsible=d["responsible"],
                                         note=d["note"], planned_date=d["planned_date"], delivery_address=d["delivery_address"])
        except TransitionError as exc:
            raise service_error(exc)
        act = act_detail_queryset(Act.objects.all()).get(pk=act.pk)
        return Response(ActDetailSerializer(act, context={"request": request, "cabinet": self.cabinet}).data, status=status.HTTP_201_CREATED)


class ActListView(ActBaseView):
    def get(self, request):
        qs = acts_for_cabinet(self.cabinet, self.is_admin)
        p = request.query_params
        if p.get("order"):
            qs = qs.filter(order_id=p["order"])
        if p.get("status"):
            qs = qs.filter(status__in=[s for s in p["status"].split(",") if s])
        if p.get("q"):
            q = p["q"].strip()
            qs = qs.filter(Q(number__icontains=q) | Q(order__title__icontains=q) | Q(order__mahalla__name__icontains=q))
        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(qs.order_by("-updated_at"), request, view=self)
        return paginator.get_paginated_response(ActListSerializer(page, many=True, context={"request": request, "cabinet": self.cabinet}).data)


class ActDetailView(ActBaseView):
    def get(self, request, act_id):
        return self.detail(self.get_act(act_id))

    def patch(self, request, act_id):
        act = self.get_act(act_id)
        ser = ActWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            act_service.update_act(act, self.cabinet, delivery_date=d["delivery_date"], lines=_lines(d), responsible=d["responsible"],
                                   note=d["note"], planned_date=d["planned_date"], delivery_address=d["delivery_address"])
        except TransitionError as exc:
            raise service_error(exc)
        return self.detail(act)


class ActAttachmentsView(ActBaseView):
    @transaction.atomic
    def post(self, request, act_id):
        act = self.get_act(act_id)
        self.require_supplier_prepare(act)
        f = request.FILES.get("file")
        if f is None:
            raise YashilError("Файл юборилмади", error_code="invalid_format", field="file", status_code=400)
        total = sum(act.attachments.values_list("size", flat=True)) + f.size
        if total > ATTACHMENT_TOTAL_MAX:
            raise YashilError("Иловалар жами 50 МБ дан ошмаслиги керак", error_code="attachments_total", field="file", status_code=400)
        kind = request.data.get("kind") or (ActAttachment.Kind.PDF if f.name.lower().endswith(".pdf") else ActAttachment.Kind.PHOTO)
        att = ActAttachment(act=act, version_no=act.version_no, file=f, original_name=f.name[:255], size=f.size, kind=kind, uploaded_by=request.user)
        try:
            att.full_clean()
        except DjangoValidationError as exc:
            msg = "; ".join(m for v in exc.message_dict.values() for m in v) if hasattr(exc, "message_dict") else "; ".join(exc.messages)
            raise YashilError(msg, error_code="invalid_file", field="file", status_code=400)
        att.save()
        # Ilova o'zgarsa imzolanmagan hujjat versiyasi eskiradi — imzo topshirig'ida qayta tuziladi
        DocumentVersion.objects.filter(act_versions__act=act, status=DocumentVersion.Status.UNSIGNED).update(status=DocumentVersion.Status.SUPERSEDED)
        return Response(ActAttachmentSerializer(att, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ActAttachmentDeleteView(ActBaseView):
    def delete(self, request, act_id, attachment_id):
        act = self.get_act(act_id)
        self.require_supplier_prepare(act)
        att = act.attachments.filter(pk=attachment_id, version_no=act.version_no).first()
        if att is None:
            raise not_found("Илова топилмади")
        att.file.delete(save=False)
        att.delete()
        DocumentVersion.objects.filter(act_versions__act=act, status=DocumentVersion.Status.UNSIGNED).update(status=DocumentVersion.Status.SUPERSEDED)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActSignTaskView(ActBaseView):
    """Imzolash topshirig'i: yetkazib beruvchi (qoralama → mahallaga) yoki mahalla (tasdiq)."""

    def post(self, request, act_id):
        act = self.get_act(act_id)
        try:
            task = act_service.sign_task(act, self.cabinet, request)
        except (TransitionError, SigningError) as exc:
            raise service_error(exc)
        from apps.yashil.serializers_orders import DocumentVersionSerializer

        dv = DocumentVersion.objects.prefetch_related("signatures").get(pk=task["document_version_id"])
        return Response({"document_version": DocumentVersionSerializer(dv).data, **task})


class ActSignView(IdempotentPostMixin, ActBaseView):
    def perform_post(self, request, act_id):
        act = self.get_act(act_id)
        ser = ActSignSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            act_service.sign(act, self.cabinet, pkcs7=d["pkcs7"], nonce=d["nonce"], request=request, document_version_id=d["document_version_id"])
        except (TransitionError, SigningError) as exc:
            raise service_error(exc)
        return self.detail(act)


class ActReturnView(IdempotentPostMixin, ActBaseView):
    def perform_post(self, request, act_id):
        act = self.get_act(act_id)
        ser = ActReturnSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            act_service.return_act(act, self.cabinet, reason_code=d["reason_code"], comment=d["comment"])
        except TransitionError as exc:
            raise service_error(exc)
        return self.detail(act)


class ActCancelView(IdempotentPostMixin, ActBaseView):
    def perform_post(self, request, act_id):
        act = self.get_act(act_id)
        ser = ActCancelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            act_service.cancel_act(act, self.cabinet, comment=ser.validated_data["comment"])
        except TransitionError as exc:
            raise service_error(exc)
        return self.detail(act)
