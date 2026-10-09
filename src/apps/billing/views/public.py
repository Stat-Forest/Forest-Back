"""
Ochiq (autentifikatsiyasiz) ijara tushumi statistikasi — landing sahifa uchun.
Faqat yig'indilar va xo'jalik nomlari; shaxsiy ma'lumot yo'q. 5 daqiqa cache.
"""
from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import Contract, Xojalik
from apps.billing.services.rent_stats import RentStatsParamsError, parse_rent_stats_params, yearly_area_price_stats

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
