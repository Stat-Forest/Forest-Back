"""Hujjat versiyasi (kabinet ichida) va ochiq QR tekshirish (TZ §13.2)."""
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.yashil.api import CabinetMixin, HasCabinet, IsAuthenticated, not_found, yashil_exception_handler
from apps.yashil.models import DocumentVersion, YashilNotification
from apps.yashil.serializers_orders import DocumentVersionSerializer, NotificationSerializer
from apps.yashil.services.documents import public_verify_payload, render_order_form_html
from apps.yashil.views.orders import orders_for_cabinet


class _DocumentBase(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (HasCabinet,)

    def get_version(self, version_id) -> DocumentVersion:
        order_ids = orders_for_cabinet(self.cabinet, self.is_admin).values("pk")
        v = DocumentVersion.objects.filter(pk=version_id, document__order_id__in=order_ids).select_related("document").first()
        if v is None:
            raise not_found("Ҳужжат топилмади ёки очиш ҳуқуқи йўқ")
        return v


class DocumentVersionView(_DocumentBase):
    def get(self, request, version_id):
        return Response(DocumentVersionSerializer(self.get_version(version_id)).data)


class DocumentVersionHtmlView(_DocumentBase):
    """Bosma ko'rinish (brauzer chop etadi); PDF — 3-bosqich."""

    def get(self, request, version_id):
        v = self.get_version(version_id)
        html = v.html or render_order_form_html(v)
        resp = HttpResponse(html, content_type="text/html; charset=utf-8")
        resp["Content-Disposition"] = f'inline; filename="{v.document.number or "hujjat"}-v{v.version_no}.html"'
        resp["X-Frame-Options"] = "SAMEORIGIN"
        return resp


class PublicVerifyView(APIView):
    """QR'dan ochiladigan sahifa: login'siz, shaxsiy ma'lumotsiz (javob Ж6)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    def get_exception_handler(self):
        return yashil_exception_handler

    def get(self, request, token):
        v = DocumentVersion.objects.filter(qr_token=token).select_related("document").prefetch_related("signatures").first()
        if v is None:
            raise not_found("Ҳужжат топилмади")
        return Response(public_verify_payload(v))


class NotificationListView(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = ()

    def get(self, request):
        qs = YashilNotification.objects.filter(recipient_user=request.user).select_related("order")
        if request.query_params.get("unread"):
            qs = qs.filter(read_at__isnull=True)
        from apps.base.pagination import CustomPageNumberPagination

        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)


class NotificationReadView(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = ()

    def post(self, request, notification_id):
        updated = YashilNotification.objects.filter(pk=notification_id, recipient_user=request.user, read_at__isnull=True).update(read_at=timezone.now())
        if not updated and not YashilNotification.objects.filter(pk=notification_id, recipient_user=request.user).exists():
            raise not_found("Хабарнома топилмади")
        return Response({"ok": True})


class NotificationReadAllView(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = ()

    def post(self, request):
        n = YashilNotification.objects.filter(recipient_user=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response({"ok": True, "updated": n})
