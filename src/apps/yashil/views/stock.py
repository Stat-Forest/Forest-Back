"""Ombor API (TZ §9, §14): xulosa, harakatlar, kirim, boshlang'ich qoldiq, teskari operatsiya, DM quvvati."""
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.pagination import CustomPageNumberPagination
from apps.general.models import Organization
from apps.yashil.api import (
    CabinetMixin,
    HasCabinet,
    IdempotentPostMixin,
    IsAuthenticated,
    YashilError,
    invalid_format,
    not_found,
    service_error,
)
from apps.yashil.models import CatalogItem, ServiceCapacity, StockMovement, SupplierProfile, YashilMembership
from apps.yashil.serializers_stock import (
    DecisionSerializer,
    ReversalRequestSerializer,
    StockEntrySerializer,
    StockMovementSerializer,
)
from apps.yashil.services import capacity as capacity_service
from apps.yashil.services import ledger
from apps.yashil.services import scope as scope_service
from apps.yashil.services.ledger import LedgerError

T = YashilMembership.MemberType


class _StockBase(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (HasCabinet,)

    def organization(self, request):
        """Yetkazib beruvchi — o'z tashkiloti; kuzatuvchi/admin — `?organization=` (faqat o'qish)."""
        cab = self.cabinet
        wanted = request.query_params.get("organization")
        if cab is not None and cab.member_type == T.SUPPLIER:
            if wanted and wanted != str(cab.organization_id):
                raise YashilError("Бошқа ташкилот омбори кўрсатилмайди", error_code="forbidden", status_code=403)
            return cab.organization
        if self.is_admin or (cab is not None and cab.member_type == T.OBSERVER):
            if not wanted:
                raise invalid_format("`organization` параметри керак", "organization")
            org = Organization.objects.filter(pk=wanted).first()
            profiles = SupplierProfile.objects.filter(organization=org)
            if cab is not None and cab.member_type == T.OBSERVER:
                profiles = scope_service.observer_supplier_profiles(cab, profiles)
            if org is None or not profiles.exists():
                raise not_found("Етказиб берувчи топилмади")
            return org
        raise YashilError("Омбор фақат етказиб берувчи ва кузатувчи кабинетида", error_code="forbidden", status_code=403)

    def own_warehouse(self):
        cab = self.cabinet
        if cab is None or cab.member_type != T.SUPPLIER:
            raise YashilError("Омбор амалини фақат етказиб берувчи кабинети бажаради", error_code="forbidden", status_code=403)
        return ledger.default_warehouse(cab.organization)

    def movement_payload(self, movement, warnings=None, http_status=status.HTTP_200_OK):
        movement.refresh_from_db()
        data = {
            "movement": StockMovementSerializer(movement, context={"request": self.request}).data,
            "balance": ledger._dec(ledger.balance(movement.warehouse, movement.catalog_item)),
            "warnings": warnings or [],
        }
        return Response(data, status=http_status)


class StockSummaryView(_StockBase):
    def get(self, request):
        org = self.organization(request)
        warehouse = ledger.default_warehouse(org)
        rows = ledger.warehouse_summary(org, warehouse)
        return Response({
            "organization": {"id": str(org.id), "name": org.name, "supplier_type": ledger.supplier_type_of(org)},
            "warehouse": {"id": str(warehouse.id), "name": warehouse.name},
            "rows": rows,
            "shortage_count": sum(1 for r in rows if r["shortage"] != "0"),
            "pending_reversals": sum(r["pending_reversals"] for r in rows),
            "can_post": self.cabinet is not None and self.cabinet.member_type == T.SUPPLIER and self.cabinet.can_prepare,
            "can_approve": self.cabinet is not None and self.cabinet.member_type == T.SUPPLIER and self.cabinet.can_sign,
        })


class StockOrganizationsView(_StockBase):
    """Kuzatuvchi/admin uchun yetkazib beruvchilar ro'yxati (yetishmovchilik soni bilan); yetkazib beruvchi — o'zi."""

    def get(self, request):
        cab = self.cabinet
        if cab is not None and cab.member_type == T.SUPPLIER:
            profiles = SupplierProfile.objects.filter(organization_id=cab.organization_id)
        elif cab is not None and cab.member_type == T.OBSERVER:
            profiles = scope_service.observer_supplier_profiles(cab, SupplierProfile.objects.filter(is_active_supplier=True))
        elif self.is_admin:
            profiles = SupplierProfile.objects.filter(is_active_supplier=True)
        else:
            raise YashilError("Омбор фақат етказиб берувчи ва кузатувчи кабинетида", error_code="forbidden", status_code=403)
        q = (request.query_params.get("q") or "").strip()
        if q:
            profiles = profiles.filter(organization__name__icontains=q)
        rows = []
        for p in profiles.select_related("organization").order_by("supplier_type", "organization__name")[:300]:
            org = p.organization
            summary = ledger.warehouse_summary(org)
            rows.append({"id": str(org.id), "name": p.display_name, "supplier_type": p.supplier_type, "region": org.region,
                         "shortage_count": sum(1 for r in summary if r["shortage"] != "0"),
                         "pending_reversals": sum(r["pending_reversals"] for r in summary)})
        return Response({"results": rows})


class StockMovementListView(_StockBase):
    def get(self, request):
        org = self.organization(request)
        qs = StockMovement.objects.filter(warehouse__organization=org).select_related(
            "catalog_item", "requested_by_membership__user", "approved_by", "order_line__order", "acceptance__order")
        p = request.query_params
        if p.get("item"):
            qs = qs.filter(catalog_item_id=p["item"])
        if p.get("kind"):
            qs = qs.filter(kind__in=[k for k in p["kind"].split(",") if k])
        if p.get("status"):
            qs = qs.filter(status__in=[s for s in p["status"].split(",") if s])
        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(qs.order_by("-created_at"), request, view=self)
        return paginator.get_paginated_response(StockMovementSerializer(page, many=True, context={"request": request}).data)


class _EntryView(IdempotentPostMixin, _StockBase):
    post_fn = None

    def perform_post(self, request):
        warehouse = self.own_warehouse()
        ser = StockEntrySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            with transaction.atomic():
                result = self.post_fn(warehouse, d["catalog_item"], d["qty"], self.cabinet, doc_number=d["doc_number"],
                                      doc_date=d["doc_date"], note=d["note"], file=request.FILES.get("file"))
        except LedgerError as exc:
            raise service_error(exc)
        movement, warnings = result if isinstance(result, tuple) else (result, [])
        return self.movement_payload(movement, warnings, status.HTTP_201_CREATED)


class StockReceiptView(_EntryView):
    post_fn = staticmethod(ledger.post_receipt)


class StockOpeningView(_EntryView):
    post_fn = staticmethod(ledger.post_opening)


class StockReturnInView(_EntryView):
    post_fn = staticmethod(ledger.post_return_in)


class StockReversalRequestView(IdempotentPostMixin, _StockBase):
    def perform_post(self, request):
        warehouse = self.own_warehouse()
        ser = ReversalRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        mv = StockMovement.objects.filter(pk=ser.validated_data["movement"], warehouse=warehouse).select_related("warehouse").first()
        if mv is None:
            raise not_found("Ҳаракат топилмади")
        try:
            rev = ledger.request_reversal(mv, self.cabinet, note=ser.validated_data["note"])
        except LedgerError as exc:
            raise service_error(exc)
        return self.movement_payload(rev, http_status=status.HTTP_201_CREATED)


class _ReversalDecisionView(IdempotentPostMixin, _StockBase):
    approve = True

    def perform_post(self, request, movement_id):
        warehouse = self.own_warehouse()
        rev = StockMovement.objects.filter(pk=movement_id, warehouse=warehouse, kind=StockMovement.Kind.REVERSAL).select_related("warehouse").first()
        if rev is None:
            raise not_found("Тескари операция топилмади")
        ser = DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        note = ser.validated_data["note"]
        try:
            rev = ledger.approve_reversal(rev, self.cabinet, note) if self.approve else ledger.reject_reversal(rev, self.cabinet, note=note)
        except LedgerError as exc:
            raise service_error(exc)
        return self.movement_payload(rev)


class StockReversalApproveView(_ReversalDecisionView):
    approve = True


class StockReversalRejectView(_ReversalDecisionView):
    approve = False


class ServiceCapacityView(_StockBase):
    """DM xizmat quvvati: oy bo'yicha quvvat, sarf, bo'sh (javob В5). PUT — DM'ning imzolovchi a'zosi (TZ 19.2)."""

    def get(self, request):
        org = self.organization(request)
        try:
            return Response(capacity_service.capacity_payload(org, request.query_params.get("period") or ""))
        except capacity_service.CapacityError as exc:
            raise YashilError(exc.message, error_code=exc.code, field=exc.field, status_code=exc.status)

    def put(self, request):
        cab = self.cabinet
        if cab is None or cab.member_type != T.SUPPLIER or ledger.supplier_type_of(cab.organization) != SupplierProfile.SupplierType.DM:
            raise YashilError("Хизмат қувватини фақат ДМ кабинети киритади", error_code="forbidden", status_code=403)
        if not cab.can_sign:
            raise YashilError("Қувватни киритиш учун имзолаш ҳуқуқи керак", error_code="cannot_sign", status_code=403)
        d = request.data if isinstance(request.data, dict) else {}
        try:
            return Response(capacity_service.set_capacity(cab.organization, d.get("period") or "", d.get("rows") or [], request.user))
        except capacity_service.CapacityError as exc:
            raise YashilError(exc.message, error_code=exc.code, field=exc.field, status_code=exc.status)


class StockOpeningImportView(_StockBase):
    """POST stock/opening/import/ (multipart: file, dry_run) — boshlang'ich qoldiqlar Excel'dan (javob Е1)."""

    def post(self, request):
        from apps.yashil.services import imports
        from apps.yashil.views.admin import import_response, is_dry_run, read_upload

        cab = self.cabinet
        if cab is None or cab.member_type != T.SUPPLIER or not cab.can_prepare:
            raise YashilError("Бошланғич қолдиқни фақат етказиб берувчи кабинети киритади", error_code="forbidden", status_code=403)
        f = read_upload(request)
        dry = is_dry_run(request)
        return import_response(lambda: imports.import_opening_stock(f, cabinet=cab, dry_run=dry, partial=False))

