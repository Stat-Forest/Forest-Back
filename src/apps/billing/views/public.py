"""
Ochiq (autentifikatsiyasiz) endpointlar — landing sahifa uchun: ijara tushumi
statistikasi va GIS xarita. Shaxsiy va moliyaviy ma'lumot yo'q. 5 daqiqa cache.
"""
import hashlib
import uuid

from django.core.cache import cache
from django.db.models import Prefetch, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import Contract, ContractActivity, Xojalik, XojalikKontur, XojalikLocation
from apps.billing.serializers import (
    XojalikKonturDetailSerializer,
    XojalikKonturSerializer,
    XojalikLocationDetailSerializer,
    XojalikLocationSerializer,
)
from apps.billing.services.rent_stats import RentStatsParamsError, parse_rent_stats_params, yearly_area_price_stats
from apps.billing.services.geo import OUTLINES_CACHE_KEY, slim_geojson

PUBLIC_CACHE_TIMEOUT = 300


class _PublicView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


@extend_schema(tags=["Billing public"])
class PublicRentStatsView(_PublicView):
    def get(self, request, *args, **kwargs):
        try:
            from_year, to_year, xojalik_id = parse_rent_stats_params(request.query_params)
        except RentStatsParamsError as exc:
            return Response({"errors": exc.errors}, status=status.HTTP_400_BAD_REQUEST)
        cache_key = f"billing:public:rent_stats:{from_year}:{to_year}:{xojalik_id or 'all'}"
        data = cache.get(cache_key)
        if data is None:
            queryset = Contract.objects.all()
            if xojalik_id:
                queryset = queryset.filter(xojalik_id=xojalik_id)
            data = yearly_area_price_stats(queryset, from_year, to_year)
            cache.set(cache_key, data, PUBLIC_CACHE_TIMEOUT)
        return Response(data)


@extend_schema(tags=["Billing public"])
class PublicXojalikListView(_PublicView):
    def get(self, request, *args, **kwargs):
        cache_key = "billing:public:xojaliklar"
        data = cache.get(cache_key)
        if data is None:
            data = [
                {"id": str(pk), "name": name}
                for pk, name in Xojalik.objects.filter(is_active=True).order_by("name").values_list("id", "name")
            ]
            cache.set(cache_key, data, PUBLIC_CACHE_TIMEOUT)
        return Response(data)


# ---------------------------------------------------------------------------
# Ochiq GIS xarita (landing): faol shartnomalar joylashuvi, xo'jaliklar, konturlar.
# Ijarachi ismi va moliyaviy ma'lumot (hisoblangan/to'langan/qarzdorlik) berilmaydi.
# ---------------------------------------------------------------------------
PUBLIC_GEO_LIMIT = 2000


@extend_schema(tags=["Billing public"])
class PublicGeoListView(_PublicView):
    """
    `?xojalik=<uuid>&number=<matn>` — faqat faol, joylashuvi bor shartnomalar.
    `?summary=1` — faqat soni va umumiy maydon (landing: shartnomalar xaritada faqat
    qidirilganda yoki "Barchasi" tanlanganda ko'rsatiladi).
    """

    def get(self, request, *args, **kwargs):
        xojalik = (request.query_params.get("xojalik") or "").strip()
        number = (request.query_params.get("number") or "").strip()[:100]
        summary = str(request.query_params.get("summary", "")).lower() in ("1", "true")
        if xojalik:
            try:
                xojalik = str(uuid.UUID(xojalik))
            except ValueError:
                return Response({"errors": {"xojalik": "Noto'g'ri qiymat"}}, status=status.HTTP_400_BAD_REQUEST)

        # Erkin matnli `number` keshlanmaydi — har bir turli qiymat Redis'da
        # alohida (MB'lab) yozuv ochardi (audit L4/P1)
        if number:
            return Response(self._build(xojalik, number, summary))
        digest = hashlib.sha1(f"{xojalik}|{int(summary)}".encode()).hexdigest()
        cache_key = f"billing:public:geo_list:{digest}"
        data = cache.get(cache_key)
        if data is None:
            data = self._build(xojalik, number, summary)
            cache.set(cache_key, data, PUBLIC_CACHE_TIMEOUT)
        return Response(data)

    @staticmethod
    def _build(xojalik: str, number: str, summary: bool = False) -> dict:
        queryset = Contract.objects.filter(status=Contract.Status.ACTIVE).filter(
            Q(latitude__isnull=False) | Q(boundary_geojson__isnull=False)
        )
        if xojalik:
            queryset = queryset.filter(xojalik_id=xojalik)
        if number:
            queryset = queryset.filter(Q(number__icontains=number) | Q(contract_number__icontains=number))

        total_area = queryset.aggregate(total=Sum("rent_area"))["total"] or 0
        count = queryset.count()
        if summary:
            return {"count": count, "total_area": round(float(total_area), 2), "results": []}
        rows = (
            queryset.select_related("xojalik")
            .prefetch_related(Prefetch("activities", queryset=ContractActivity.objects.select_related("type")))
            .only(
                "id", "number", "contract_number", "latitude", "longitude", "boundary_geojson",
                "rent_area", "xojalik__name",
            )
            .order_by("xojalik__name", "number")[:PUBLIC_GEO_LIMIT]
        )
        results = [
            {
                "id": str(contract.id),
                "number": contract.number,
                "contract_number": contract.contract_number,
                "latitude": float(contract.latitude) if contract.latitude is not None else None,
                "longitude": float(contract.longitude) if contract.longitude is not None else None,
                "boundary_geojson": slim_geojson(contract.boundary_geojson),
                "rent_area": float(contract.rent_area or 0),
                "xojalik_name": contract.xojalik.name,
                "activity_name": ", ".join(a.type.name for a in contract.activities.all()),
            }
            for contract in rows
        ]
        return {"count": count, "total_area": round(float(total_area), 2), "results": results}


class _PublicReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]


@extend_schema(tags=["Billing public"])
class PublicXojalikLocationViewSet(_PublicReadOnlyViewSet):
    filterset_fields = ["region"]
    queryset = XojalikLocation.objects.select_related("region", "xojalik")

    def get_serializer_class(self):
        return XojalikLocationDetailSerializer if self.action == "retrieve" else XojalikLocationSerializer

    def get_queryset(self):
        queryset = super().get_queryset().defer("outline_geojson")
        return queryset.defer("boundary_geojson") if self.action == "list" else queryset


@extend_schema(tags=["Billing public"])
class PublicXojalikOutlinesView(_PublicView):
    """
    Barcha xo'jaliklarning ixcham tashqi chegarasi (FeatureCollection, ~200 KB) —
    landing xaritasi birinchi ochilganda yerlar shu chegaralar bilan ko'rinadi.
    """

    def get(self, request, *args, **kwargs):
        data = cache.get(OUTLINES_CACHE_KEY)
        if data is None:
            rows = (
                XojalikLocation.objects.filter(outline_geojson__isnull=False)
                .order_by("name").values_list("id", "name", "area_ga", "outline_geojson")
            )
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "id": str(pk),
                        "properties": {"id": str(pk), "name": name, "area_ga": float(area) if area is not None else None},
                        "geometry": outline,
                    }
                    for pk, name, area, outline in rows
                ],
            }
            cache.set(OUTLINES_CACHE_KEY, data, PUBLIC_CACHE_TIMEOUT)
        return Response(data)


@extend_schema(tags=["Billing public"])
class PublicXojalikKonturViewSet(_PublicReadOnlyViewSet):
    filterset_fields = ["xojalik_location"]
    queryset = XojalikKontur.objects.all()

    def get_serializer_class(self):
        return XojalikKonturDetailSerializer if self.action == "retrieve" else XojalikKonturSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            return queryset.select_related("xojalik_location", "xojalik_location__region")
        if not self.request.query_params.get("xojalik_location"):
            return queryset.none()  # 41k kontur — faqat bitta xo'jalik bo'yicha
        return queryset.only("id", "kontur_raqami", "area_ga", "xojalik_location_id", "raqami_num", "seq")
