"""Buyurtma API (TZ §21): qoralama, tahrir, ilovalar, hujjat, imzolab yuborish, ko'rib chiqish o'tishlari."""
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.pagination import CustomPageNumberPagination
from apps.yashil.api import (
    CabinetMixin,
    CanPrepare,
    HasCabinet,
    IdempotentPostMixin,
    IsAuthenticated,
    YashilError,
    not_found,
    service_error,
)
from apps.yashil.models import (
    ATTACHMENT_TOTAL_MAX,
    EDITABLE_STATES,
    DocumentVersion,
    Order,
    OrderAttachment,
    OrderEvent,
    OrderLine,
    OrderState,
    Signature,
    SupplierProfile,
    YashilMembership,
)
from apps.yashil.serializers_orders import (
    AcceptSerializer,
    AttachmentSerializer,
    OrderDetailSerializer,
    OrderEventSerializer,
    OrderListSerializer,
    OrderWriteSerializer,
    ReturnSerializer,
    SubmitSerializer,
)
from apps.yashil.services import scope as scope_service
from apps.yashil.services.scope import orders_for_cabinet  # noqa: F401 — boshqa view'lar shu nomdan foydalanadi
from apps.yashil.services import transitions as tr
from apps.yashil.services.documents import build_order_form
from apps.yashil.services.norms import OrderValidationError, validate_for_submit, validate_lines
from apps.yashil.services.signing import SigningError, prepare_signing, verify_and_store
from apps.yashil.services.transitions import TransitionError

T = YashilMembership.MemberType


def detail_queryset(qs):
    return qs.prefetch_related(
        Prefetch("lines", queryset=OrderLine.objects.select_related("catalog_item")),
        "versions", "attachments", "events__actor_user",
        Prefetch("documents__versions", queryset=DocumentVersion.objects.prefetch_related("signatures")),
        "documents__current_version__signatures",
    ).select_related("object_type", "season", "linked_order", "created_by_membership")


class OrderBaseView(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (HasCabinet,)

    def get_order(self, order_id, for_update=False) -> Order:
        qs = orders_for_cabinet(self.cabinet, self.is_admin)
        if for_update:
            qs = qs.select_for_update(of=("self",))
        order = qs.filter(pk=order_id).first()
        if order is None:
            raise not_found("Буюртма топилмади ёки очиш ҳуқуқи йўқ")
        return order

    def detail(self, order, http_status=status.HTTP_200_OK):
        order = detail_queryset(orders_for_cabinet(self.cabinet, self.is_admin)).get(pk=order.pk)
        return Response(OrderDetailSerializer(order, context={"request": self.request, "cabinet": self.cabinet}).data, status=http_status)

    def check_version(self, order, data):
        v = data.get("version_no")
        if v is not None and int(v) != order.version_no:
            raise YashilError("Буюртма бошқа фойдаланувчи томонидан ўзгартирилган — саҳифани янгиланг",
                              error_code="version_conflict", field="version_no", status_code=status.HTTP_409_CONFLICT)

    def require_mahalla_prepare(self, order=None):
        cab = self.cabinet
        if cab is None or cab.member_type != T.MAHALLA or not cab.can_prepare:
            raise YashilError("Буюртмани фақат маҳалла кабинети тайёрлайди", error_code="forbidden", status_code=403)
        if order is not None and order.mahalla_id != cab.mahalla_id:
            raise not_found()
        if order is not None and order.state not in EDITABLE_STATES:
            raise YashilError("Буюртма бу ҳолатда таҳрирланмайди", error_code="state_conflict", status_code=409)


class OrderListCreateView(OrderBaseView):
    pagination_class = CustomPageNumberPagination

    def get(self, request):
        qs = orders_for_cabinet(self.cabinet, self.is_admin)
        p = request.query_params
        if p.get("state"):
            qs = qs.filter(state__in=[s for s in p["state"].split(",") if s])
        if p.get("route"):
            qs = qs.filter(route=p["route"])
        if p.get("mahalla"):
            qs = qs.filter(mahalla_id=p["mahalla"])
        if p.get("q"):
            q = p["q"].strip()
            qs = qs.filter(Q(number__icontains=q) | Q(title__icontains=q) | Q(mahalla__name__icontains=q) | Q(address__icontains=q))
        qs = qs.order_by("-last_submitted_at", "-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(OrderListSerializer(page, many=True).data)

    @transaction.atomic
    def post(self, request):
        self.require_mahalla_prepare()
        ser = OrderWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        lines = data.pop("lines", None) or []
        data.pop("version_no", None)
        self._check_supplier(data["route"], data["supplier_org"])
        order = Order(mahalla=self.cabinet.mahalla, created_by_membership=self.cabinet, created_by=request.user, **data)
        order.save()
        self._replace_lines(order, lines)
        return self.detail(order, status.HTTP_201_CREATED)

    @staticmethod
    def _check_supplier(route, org):
        profile = SupplierProfile.objects.filter(organization=org, is_active_supplier=True).first()
        if profile is None or profile.supplier_type != route:
            raise YashilError("Етказиб берувчи танланган йўналишга мос эмас", error_code="supplier_invalid", field="supplier_org")

    @staticmethod
    def _replace_lines(order, lines):
        if lines:
            try:
                validate_lines(lines, supplier_type=order.route, base_seedlings=order.base_seedlings, problem_note=order.problem_note)
            except OrderValidationError as exc:
                raise service_error(exc)
        order.lines.all().delete()
        OrderLine.objects.bulk_create([
            OrderLine(order=order, catalog_item=l["catalog_item"], qty=l["qty"], attrs_note=l.get("attrs_note", ""), position=i)
            for i, l in enumerate(lines)
        ])


class OrderDetailView(OrderBaseView):
    def get(self, request, order_id):
        return self.detail(self.get_order(order_id))

    @transaction.atomic
    def patch(self, request, order_id):
        order = self.get_order(order_id, for_update=True)
        self.require_mahalla_prepare(order)
        self.check_version(order, request.data)
        ser = OrderWriteSerializer(order, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        lines = data.pop("lines", None)
        data.pop("version_no", None)
        route, org = data.get("route", order.route), data.get("supplier_org", order.supplier_org)
        if "route" in data or "supplier_org" in data:
            OrderListCreateView._check_supplier(route, org)
        for k, v in data.items():
            setattr(order, k, v)
        order.updated_by = request.user
        order.save()
        if lines is not None:
            OrderListCreateView._replace_lines(order, lines)
        OrderEvent.objects.create(order=order, action="edit", from_state=order.state, to_state=order.state,
                                  actor_user=request.user, actor_membership=self.cabinet, actor_label=self.cabinet.cabinet_name,
                                  payload={"fields": sorted(list(data.keys()) + (["lines"] if lines is not None else []))})
        return self.detail(order)


class OrderAttachmentsView(OrderBaseView):
    @transaction.atomic
    def post(self, request, order_id):
        order = self.get_order(order_id)
        self.require_mahalla_prepare(order)
        f = request.FILES.get("file")
        if f is None:
            raise YashilError("Файл юборилмади", error_code="invalid_format", field="file", status_code=400)
        total = sum(order.attachments.values_list("size", flat=True)) + f.size
        if total > ATTACHMENT_TOTAL_MAX:
            raise YashilError("Иловалар жами 50 МБ дан ошмаслиги керак", error_code="attachments_total", field="file", status_code=400)
        att = OrderAttachment(order=order, version_no=order.version_no, file=f, original_name=f.name[:255], size=f.size,
                              kind=request.data.get("kind") or OrderAttachment.Kind.OTHER, uploaded_by=request.user)
        try:
            att.full_clean()
        except Exception as exc:  # ValidationError
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                msg = "; ".join(m for v in exc.message_dict.values() for m in v) if hasattr(exc, "message_dict") else "; ".join(exc.messages)
                raise YashilError(msg, error_code="invalid_file", field="file", status_code=400)
            raise
        att.save()
        return Response(AttachmentSerializer(att, context={"request": request}).data, status=status.HTTP_201_CREATED)


class OrderAttachmentDeleteView(OrderBaseView):
    def delete(self, request, order_id, attachment_id):
        order = self.get_order(order_id)
        self.require_mahalla_prepare(order)
        att = order.attachments.filter(pk=attachment_id).first()
        if att is None:
            raise not_found("Илова топилмади")
        att.file.delete(save=False)
        att.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderDocumentView(OrderBaseView):
    """Buyurtmanomani yaratish va imzolash topshirig'i (TZ §6.1-3, §13.1)."""

    def post(self, request, order_id):
        order = self.get_order(order_id)
        cab = self.cabinet
        if cab is None or cab.member_type != T.MAHALLA or order.mahalla_id != cab.mahalla_id:
            raise YashilError("Ҳужжатни маҳалла кабинети тайёрлайди", error_code="forbidden", status_code=403)
        if not cab.can_sign:
            raise YashilError("Бу кабинетда имзолаш ҳуқуқи йўқ", error_code="cannot_sign", status_code=403)
        if order.state not in EDITABLE_STATES:
            raise YashilError("Буюртма бу ҳолатда юборилмайди", error_code="state_conflict", status_code=409)
        self.check_version(order, request.data)
        try:
            validate_for_submit(order)
        except OrderValidationError as exc:
            raise service_error(exc)
        with transaction.atomic():
            # Raqam serverda hujjat tayyorlanganda beriladi (TZ §4); bekor bo'lsa ham qayta ishlatilmaydi.
            if not order.number:
                from apps.yashil.services.numbering import next_order_number
                from apps.yashil.services.workdays import local_date
                from django.utils import timezone as _tz

                Order.objects.filter(pk=order.pk, number__isnull=True).update(number=next_order_number(local_date(_tz.now())))
                order.refresh_from_db(fields=["number"])
            version = build_order_form(order, cab)
        try:
            task = prepare_signing(version, request.user, cab, Signature.Role.MAHALLA, request)
        except SigningError as exc:
            raise service_error(exc)
        from apps.yashil.serializers_orders import DocumentVersionSerializer

        return Response({"document_version": DocumentVersionSerializer(version).data, **task})


class OrderSubmitView(IdempotentPostMixin, OrderBaseView):
    def perform_post(self, request, order_id):
        order = self.get_order(order_id)
        ser = SubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        self.check_version(order, d)
        version = DocumentVersion.objects.filter(pk=d["document_version_id"], document__order=order).first()
        if version is None:
            raise not_found("Ҳужжат версияси топилмади")
        try:
            with transaction.atomic():
                verify_and_store(version, request.user, self.cabinet, Signature.Role.MAHALLA, d["pkcs7"], d["nonce"], request)
                tr.submit(order, self.cabinet, document_version=version)
        except (SigningError, TransitionError) as exc:
            raise service_error(exc)
        return self.detail(order)


class _TransitionView(IdempotentPostMixin, OrderBaseView):
    action = ""

    def run(self, order, data):  # pragma: no cover - subclass
        raise NotImplementedError

    def perform_post(self, request, order_id):
        order = self.get_order(order_id)
        self.check_version(order, request.data)
        try:
            self.run(order, request.data)
        except TransitionError as exc:
            raise service_error(exc)
        return self.detail(order)


class OrderReviewView(_TransitionView):
    def run(self, order, data):
        tr.start_review(order, self.cabinet)


class OrderForwardView(_TransitionView):
    def run(self, order, data):
        tr.forward(order, self.cabinet)


class OrderReturnView(_TransitionView):
    def run(self, order, data):
        ser = ReturnSerializer(data=data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        tr.return_order(order, self.cabinet, reason_code=d.get("reason_code", ""), comment=d.get("comment", ""), fields=d.get("fields"))


class OrderAcceptView(_TransitionView):
    def run(self, order, data):
        ser = AcceptSerializer(data=data)
        ser.is_valid(raise_exception=True)
        tr.accept(order, self.cabinet, executor_name=ser.validated_data.get("executor_name", ""))


class OrderEventsView(OrderBaseView):
    def get(self, request, order_id):
        order = self.get_order(order_id)
        return Response(OrderEventSerializer(order.events.select_related("actor_user"), many=True).data)
