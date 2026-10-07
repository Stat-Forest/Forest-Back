"""Ma'lumotnoma ro'yxatlari (sahifalanmagan) va ijarachilar (sahifalangan)."""
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics

from apps.billing.filters import BolimFilter
from apps.billing.models import ActivityType, Bolim, District, LandType, PrivilegeType, Region, Renter, Xojalik
from apps.billing.permissions import BillingReadOrWrite
from apps.billing.serializers import (
    ActivityTypeSerializer,
    BolimSerializer,
    DistrictSerializer,
    LandTypeSerializer,
    PrivilegeTypeSerializer,
    RegionSerializer,
    RenterSerializer,
    XojalikSerializer,
)


class _ReferenceListView(generics.ListAPIView):
    permission_classes = [BillingReadOrWrite]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]


@extend_schema(tags=["Billing"])
class RegionListView(_ReferenceListView):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    filter_backends = []


@extend_schema(tags=["Billing"])
class DistrictListView(_ReferenceListView):
    queryset = District.objects.select_related("region")
    serializer_class = DistrictSerializer
    filterset_fields = ["region"]
    search_fields = ["name", "code"]


@extend_schema(tags=["Billing"])
class XojalikListView(_ReferenceListView):
    queryset = Xojalik.objects.select_related("region")
    serializer_class = XojalikSerializer
    filterset_fields = ["region", "is_active"]
    search_fields = ["name", "inn", "code"]


@extend_schema(tags=["Billing"])
class BolimListView(_ReferenceListView):
    queryset = Bolim.objects.select_related("xojalik")
    serializer_class = BolimSerializer
    filterset_class = BolimFilter
    search_fields = ["name"]


@extend_schema(tags=["Billing"])
class LandTypeListView(_ReferenceListView):
    queryset = LandType.objects.select_related("parent")
    serializer_class = LandTypeSerializer
    filterset_fields = ["parent"]
    search_fields = ["name"]


@extend_schema(tags=["Billing"])
class ActivityTypeListView(_ReferenceListView):
    queryset = ActivityType.objects.select_related("parent")
    serializer_class = ActivityTypeSerializer
    filterset_fields = ["parent"]
    search_fields = ["name"]


@extend_schema(tags=["Billing"])
class PrivilegeTypeListView(_ReferenceListView):
    queryset = PrivilegeType.objects.select_related("parent")
    serializer_class = PrivilegeTypeSerializer
    filterset_fields = ["parent"]
    search_fields = ["name"]


@extend_schema(tags=["Billing"])
class RenterListView(generics.ListAPIView):
    permission_classes = [BillingReadOrWrite]
    serializer_class = RenterSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["full_name", "pinfl", "stir", "legal_name"]
    queryset = Renter.objects.annotate(contracts_count=Count("contracts")).order_by("full_name")
