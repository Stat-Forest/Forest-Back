"""GIS: xo'jaliklar joylashuvi (ro'yxat yengil, geometriya faqat detail'da) va konturlar."""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from apps.billing.models import XojalikKontur, XojalikLocation
from apps.billing.permissions import BillingReadOrWrite
from apps.billing.scope import scope_queryset
from apps.billing.serializers import (
    XojalikKonturDetailSerializer,
    XojalikKonturSerializer,
    XojalikLocationDetailSerializer,
    XojalikLocationSerializer,
)


@extend_schema(tags=["Billing"])
class XojalikLocationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [BillingReadOrWrite]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["region", "xojalik"]
    queryset = XojalikLocation.objects.select_related("region", "xojalik")

    def get_serializer_class(self):
        return XojalikLocationDetailSerializer if self.action == "retrieve" else XojalikLocationSerializer

    def get_queryset(self):
        queryset = scope_queryset(super().get_queryset(), self.request.user)
        if self.action == "list":
            queryset = queryset.defer("boundary_geojson")
        return queryset


@extend_schema(tags=["Billing"])
class XojalikKonturViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [BillingReadOrWrite]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["xojalik_location"]
    queryset = XojalikKontur.objects.all()

    def get_serializer_class(self):
        return XojalikKonturDetailSerializer if self.action == "retrieve" else XojalikKonturSerializer

    def get_queryset(self):
        queryset = scope_queryset(super().get_queryset(), self.request.user, "xojalik_location__xojalik_id")
        if self.action == "retrieve":
            return queryset.select_related("xojalik_location", "xojalik_location__region")
        return queryset.only("id", "kontur_raqami", "area_ga", "xojalik_location_id", "raqami_num", "seq")
