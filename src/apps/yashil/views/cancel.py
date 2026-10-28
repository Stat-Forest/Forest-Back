"""Bekor qilish API (TZ §9.3; javob Е4): qabulgacha mahalla o'zi; keyin so'rov → kelishuv → uyushma tasdig'i."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.pagination import CustomPageNumberPagination
from apps.yashil.api import CabinetMixin, HasCabinet, IdempotentPostMixin, IsAuthenticated, not_found, service_error
from apps.yashil.models import CancelRequest, OrderState
from apps.yashil.serializers_cancel import CancelDecisionSerializer, CancelRequestSerializer, CancelRequestWriteSerializer
from apps.yashil.services import cancel as cancel_service
from apps.yashil.services.transitions import TransitionError
from apps.yashil.views.orders import OrderBaseView, orders_for_cabinet


def cancel_requests_for_cabinet(cabinet, is_admin):
    order_ids = orders_for_cabinet(cabinet, is_admin).values("pk")
    return CancelRequest.objects.filter(order_id__in=order_ids).select_related(
        "order__mahalla", "order__supplier_org", "requested_by_membership__user", "agreed_by", "approved_by",
        "document__current_version").prefetch_related("document__versions__signatures", "document__current_version__signatures")


class OrderCancelView(IdempotentPostMixin, OrderBaseView):
    """`POST orders/{id}/cancel/`: qoralama/qaytarilgan — darhol bekor (buyurtma qaytadi); ijroda — so'rov (201)."""

    def perform_post(self, request, order_id):
        order = self.get_order(order_id)
        ser = CancelRequestWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            if order.state in (OrderState.DRAFT, OrderState.RETURNED):
                cancel_service.cancel_before_acceptance(order, self.cabinet, reason=d["reason"])
                return self.detail(order)
            req = cancel_service.request_cancel(order, self.cabinet, lines=[{"order_line": l["order_line"], "qty": l["qty"]} for l in d["lines"]],
                                                reason=d["reason"])
        except TransitionError as exc:
            raise service_error(exc)
        req = cancel_requests_for_cabinet(self.cabinet, self.is_admin).get(pk=req.pk)
        return Response(CancelRequestSerializer(req, context={"request": request}).data, status=status.HTTP_201_CREATED)


class _CancelBase(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (HasCabinet,)

    def get_request(self, request_id) -> CancelRequest:
        req = cancel_requests_for_cabinet(self.cabinet, self.is_admin).filter(pk=request_id).first()
        if req is None:
            raise not_found("Бекор қилиш сўрови топилмади ёки очиш ҳуқуқи йўқ")
        return req

    def detail(self, req):
        req = cancel_requests_for_cabinet(self.cabinet, self.is_admin).get(pk=req.pk)
        return Response(CancelRequestSerializer(req, context={"request": self.request}).data)


class CancelListView(_CancelBase):
    def get(self, request):
        qs = cancel_requests_for_cabinet(self.cabinet, self.is_admin)
        p = request.query_params
        if p.get("order"):
            qs = qs.filter(order_id=p["order"])
        if p.get("status"):
            qs = qs.filter(status__in=[s for s in p["status"].split(",") if s])
        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(qs.order_by("-created_at"), request, view=self)
        return paginator.get_paginated_response(CancelRequestSerializer(page, many=True, context={"request": request}).data)


class CancelDetailView(_CancelBase):
    def get(self, request, request_id):
        return self.detail(self.get_request(request_id))


class _CancelDecisionView(IdempotentPostMixin, _CancelBase):
    action = ""

    def perform_post(self, request, request_id):
        req = self.get_request(request_id)
        ser = CancelDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        note = ser.validated_data["note"]
        try:
            if self.action == "agree":
                cancel_service.agree_cancel(req, self.cabinet)
            elif self.action == "approve":
                cancel_service.approve_cancel(req, self.cabinet)
            else:
                cancel_service.reject_cancel(req, self.cabinet, note=note)
        except TransitionError as exc:
            raise service_error(exc)
        return self.detail(req)


class CancelAgreeView(_CancelDecisionView):
    action = "agree"


class CancelApproveView(_CancelDecisionView):
    action = "approve"


class CancelRejectView(_CancelDecisionView):
    action = "reject"
