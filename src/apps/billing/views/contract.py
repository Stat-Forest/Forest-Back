"""Shartnomalar: ro'yxat/filtr, yaratish/tahrirlash, holat, yillik summalar, GIS, Excel."""
from decimal import Decimal
from pathlib import Path

from django.db.models import Count, DecimalField, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.billing.filters import BillingContractFilter
from apps.billing.models import Contract, ContractActivity, ContractLand, ContractPrivilege, ContractYearlyAmount
from apps.billing.permissions import BillingReadOrWrite, BillingPIIReadOrWrite
from apps.billing.scope import scope_queryset
from apps.billing.serializers import (
    ChangeRenterSerializer,
    ContractDetailSerializer,
    ContractHistorySerializer,
    ContractListSerializer,
    ContractStatusSerializer,
    ContractYearlyAmountSerializer,
    ImportRowsSerializer,
)
from apps.billing.services import contract_writer
from apps.billing.services.errors import BillingValidationError
from apps.billing.services.excel_export import build_contracts_workbook
from apps.billing.services.excel_import import import_rows
from apps.billing.services.rent_stats import RentStatsParamsError, parse_rent_stats_params, yearly_area_price_stats
from apps.billing.services.geo import slim_geojson

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
IMPORT_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates_xlsx" / "import_template.xlsx"
UUID_REGEX = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=22, decimal_places=2))


def _errors_response(exc: BillingValidationError) -> Response:
    return Response({"errors": exc.errors}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Billing"])
class ContractViewSet(viewsets.GenericViewSet):
    """
    GET — har qanday autentifikatsiyalangan foydalanuvchi; POST/PATCH —
    billing_user / billing_super / super_admin (`BillingReadOrWrite`).
    billing_user faqat o'ziga biriktirilgan xo'jaliklarni ko'radi
    (doiradan tashqari shartnoma — 404).
    """

    permission_classes = [BillingReadOrWrite]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BillingContractFilter
    serializer_class = ContractListSerializer
    lookup_value_regex = UUID_REGEX

    def get_queryset(self):
        queryset = Contract.objects.select_related(
            "xojalik", "xojalik__region", "bolim", "region", "district", "renter",
        ).order_by("xojalik__name", "-created_at")
        queryset = scope_queryset(queryset, self.request.user)
        if self.action == "retrieve":
            return self._prefetch_detail(queryset)
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ContractListSerializer
        return ContractDetailSerializer

    @staticmethod
    def _prefetch_detail(queryset):
        return queryset.prefetch_related(
            "yearly_amounts",
            Prefetch("lands", queryset=ContractLand.objects.select_related("type", "type__parent")),
            Prefetch("activities", queryset=ContractActivity.objects.select_related("type")),
            Prefetch("privileges", queryset=ContractPrivilege.objects.select_related("type")),
            "actions__products",
            "files__uploaded_by",
        )

    def _detail(self, contract: Contract, http_status=status.HTTP_200_OK) -> Response:
        instance = self._prefetch_detail(Contract.objects.select_related(
            "xojalik", "xojalik__region", "bolim", "region", "district", "renter",
        )).get(pk=contract.pk)
        return Response(ContractDetailSerializer(instance, context=self.get_serializer_context()).data, status=http_status)

    # ------------------------------------------------------------------ CRUD
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).annotate(files_count=Count("files", distinct=True))
        page = self.paginate_queryset(queryset)
        serializer = ContractListSerializer(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        contract = self.get_object()
        return Response(ContractDetailSerializer(contract, context=self.get_serializer_context()).data)

    def create(self, request, *args, **kwargs):
        try:
            contract = contract_writer.save_contract(request.data, request.user)
        except BillingValidationError as exc:
            return _errors_response(exc)
        return self._detail(contract, status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        contract = self.get_object()
        try:
            contract = contract_writer.save_contract(request.data, request.user, instance=contract)
        except BillingValidationError as exc:
            return _errors_response(exc)
        return self._detail(contract)

    # --------------------------------------------------------------- actions
    @action(detail=True, methods=["post"], url_path="status")
    def change_status(self, request, *args, **kwargs):
        contract = self.get_object()
        serializer = ContractStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": {"contract": serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)
        contract_writer.change_status(
            contract, request.user, serializer.validated_data["status"], serializer.validated_data.get("cancel_reason"),
        )
        return self._detail(contract)

    @action(detail=True, methods=["patch"], url_path="yearly-amounts")
    def yearly_amounts(self, request, *args, **kwargs):
        contract = self.get_object()
        try:
            contract = contract_writer.update_yearly_amounts(contract, request.user, request.data.get("yearly_amounts"))
        except BillingValidationError as exc:
            return _errors_response(exc)
        return Response({
            "yearly_amounts": ContractYearlyAmountSerializer(contract.yearly_amounts.all(), many=True).data,
            "rent_amount": str(contract.rent_amount),
            "paid_amount": str(contract.paid_amount),
            "penalty_amount": str(contract.penalty_amount),
            "debt": str(contract.debt),
        })

    @action(detail=True, methods=["post"], url_path="change-renter")
    def change_renter(self, request, *args, **kwargs):
        contract = self.get_object()
        serializer = ChangeRenterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": {"renter": serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)
        renter = serializer.validated_data["renter"]
        if not contract_writer.renter_in_scope(renter, contract, request.user):
            # billing_user o'z doirasidan tashqaridagi ijarachini biriktirib, uning
            # to'liq ma'lumotini ko'ra olmasin (audit B7)
            return Response({"errors": {"renter": ["Ijarachi topilmadi"]}}, status=status.HTTP_400_BAD_REQUEST)
        contract_writer.change_renter(contract, request.user, renter)
        return self._detail(contract)

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, *args, **kwargs):
        contract = self.get_object()
        queryset = contract.history.select_related("executor").order_by("-created_at")
        return Response(ContractHistorySerializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        base = queryset.aggregate(
            total_count=Count("id"),
            total_rent_area=Coalesce(Sum("rent_area"), ZERO),
        )
        year = request.query_params.get("year")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        if year:
            amounts = ContractYearlyAmount.objects.filter(contract__in=queryset.values("id"), year=year).aggregate(
                total_rent_amount=Coalesce(Sum("calculated_amount"), ZERO),
                total_paid_amount=Coalesce(Sum("paid_amount"), ZERO),
                total_penalty_amount=Coalesce(Sum("penalty_amount"), ZERO),
            )
        else:
            amounts = queryset.aggregate(
                total_rent_amount=Coalesce(Sum("rent_amount"), ZERO),
                total_paid_amount=Coalesce(Sum("paid_amount"), ZERO),
                total_penalty_amount=Coalesce(Sum("penalty_amount"), ZERO),
            )
        data = {**base, **amounts}
        data["total_debt"] = data["total_rent_amount"] - data["total_paid_amount"]
        return Response({key: str(value) if isinstance(value, Decimal) else value for key, value in data.items()})

    @action(detail=False, methods=["get"], url_path="rent-stats")
    def rent_stats(self, request, *args, **kwargs):
        """Ijara tushumi statistikasi (yillar bo'yicha), foydalanuvchi doirasida."""
        try:
            from_year, to_year, xojalik_id = parse_rent_stats_params(request.query_params)
        except RentStatsParamsError as exc:
            return Response({"errors": exc.errors}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        if xojalik_id:
            queryset = queryset.filter(xojalik_id=xojalik_id)
        return Response(yearly_area_price_stats(queryset, from_year, to_year))

    @action(detail=False, methods=["get"], url_path="counts")
    def counts(self, request, *args, **kwargs):
        params = request.query_params.copy()
        params.pop("status", None)
        queryset = BillingContractFilter(params, queryset=self.get_queryset(), request=request).qs
        today = timezone.localdate()
        active, inactive = Contract.Status.ACTIVE, Contract.Status.INACTIVE
        agg = queryset.aggregate(
            all=Count("id"),
            active=Count("id", filter=Q(status=active)),
            inactive=Count("id", filter=Q(status=inactive)),
            today_all=Count("id", filter=Q(created_at__date=today)),
            today_active=Count("id", filter=Q(created_at__date=today, status=active)),
            today_inactive=Count("id", filter=Q(created_at__date=today, status=inactive)),
        )
        return Response({
            "all": agg["all"],
            "active": agg["active"],
            "inactive": agg["inactive"],
            "added_today": {"all": agg["today_all"], "active": agg["today_active"], "inactive": agg["today_inactive"]},
        })

    @action(detail=False, methods=["get"], url_path="geo-list")
    def geo_list(self, request, *args, **kwargs):
        """GIS xarita uchun: faqat joylashuvi (nuqta yoki chegara) bor shartnomalar; status berilmasa faqat faol."""
        queryset = self.filter_queryset(self.get_queryset())
        if not request.query_params.get("status"):
            queryset = queryset.filter(status=Contract.Status.ACTIVE)
        queryset = queryset.filter(
            Q(latitude__isnull=False) | Q(boundary_geojson__isnull=False)
        ).prefetch_related(Prefetch("activities", queryset=ContractActivity.objects.select_related("type")))

        results = []
        for contract in queryset:
            renter = contract.renter
            results.append({
                "id": contract.id,
                "number": contract.number,
                "contract_number": contract.contract_number,
                "status": contract.status,
                "latitude": float(contract.latitude) if contract.latitude is not None else None,
                "longitude": float(contract.longitude) if contract.longitude is not None else None,
                "boundary_geojson": slim_geojson(contract.boundary_geojson),
                "rent_area": float(contract.rent_area or 0),
                "debt": float(contract.debt),
                "xojalik_name": contract.xojalik.name,
                "renter_name": renter.legal_name or renter.full_name,
                "activity_name": ", ".join(a.type.name for a in contract.activities.all()),
            })
        return Response({"count": len(results), "results": results})

    @action(detail=False, methods=["get"], url_path="export-excel", permission_classes=[BillingPIIReadOrWrite])
    def export_excel(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        content = build_contracts_workbook(queryset)
        response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="shartnomalar-{timezone.localtime():%Y%m%d-%H%M}.xlsx"'
        return response

    @action(detail=False, methods=["get"], url_path="import-template")
    def import_template(self, request, *args, **kwargs):
        response = FileResponse(open(IMPORT_TEMPLATE_PATH, "rb"), content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = 'attachment; filename="shartnoma-import-namuna.xlsx"'
        return response

    @action(detail=False, methods=["post"], url_path="import-excel")
    def import_excel(self, request, *args, **kwargs):
        serializer = ImportRowsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(import_rows(serializer.validated_data["rows"], request.user))
