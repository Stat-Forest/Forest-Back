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
from apps.yashil.services import ledger
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
            if org is None or not SupplierProfile.objects.filter(organization=org).exists():
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
        elif self.is_admin or (cab is not None and cab.member_type == T.OBSERVER):
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
    """DM xizmat quvvati: oy bo'yicha quvvat, sarf, bo'sh (javob В5)."""

    def get(self, request):
        org = self.organization(request)
        period = (request.query_params.get("period") or "").strip()
        if len(period) != 7 or period[4] != "-" or not period.replace("-", "").isdigit():
            raise invalid_format("`period` YYYY-MM кўринишида бўлиши керак", "period")
        items = CatalogItem.objects.filter(supplier_type=ledger.supplier_type_of(org), item_type=CatalogItem.ItemType.SERVICE, is_active=True).order_by("order", "code")
        caps = {c.catalog_item_id: c.capacity for c in ServiceCapacity.objects.filter(organization=org, period=period)}
        rows = []
        for item in items:
            cap = caps.get(item.id)
            available = ledger.capacity_available(org, item, period)
            used = (cap - available) if cap is not None else ledger.ZERO
            rows.append({"catalog_item_id": str(item.id), "code": item.code, "name_cyr": item.name_cyr, "name_lat": item.name_lat,
                         "unit": item.unit, "capacity": ledger._dec(cap or 0), "used": ledger._dec(used), "available": ledger._dec(available)})
        return Response({"period": period, "rows": rows})
