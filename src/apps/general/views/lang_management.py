# ==============================
# views.py
# ==============================
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from rest_framework import status
from django.db.models import Sum
from django.core.cache import cache

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.general.models import LandManagement
from apps.general.serializers.land_management import LandManagementItemSerializer



@extend_schema(tags=["Land management"])
class LandManagementSummaryAPIView(APIView):

    """
    API endpoint to return land management summary with caching.

    GET:
        - Returns all land plots and total area
        - Supports optional query parameter 'lang' for translation
        - Cached to reduce database queries

    Security:
        - Accessible for all authenticated users (can add permission_classes if needed)
    """
    permission_classes = [permissions.AllowAny]
    CACHE_TIMEOUT = 60 * 60

    @extend_schema(
        summary="Yer maydonlari statistikasi",
        parameters=[
            OpenApiParameter(
                name="lang",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Til: uz yoki ru",
                enum=["uz", "ru"]
            )
        ],
        responses={200: dict}
    )
    def get(self, request):
        lang = request.GET.get("lang", "uz")
        cache_key = f"land_management_summary:{lang}"

        # ======================================================
        # Try fetching cached data
        # ======================================================
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # ======================================================
        # Cache miss - fetch from DB
        # ======================================================
        queryset = LandManagement.objects.all()
        total = queryset.aggregate(total=Sum('area'))['total'] or 0

        serializer = LandManagementItemSerializer(
            queryset,
            many=True,
            context={"request": request, "lang": lang}
        )

        title_map = {
            "uz": f"Jami {total} ga",
            "ru": f"Итого {total} га"
        }

        data = {
            "title": title_map.get(lang, title_map["uz"]),
            "total": total,
            "items": serializer.data
        }

        # ======================================================
        # Save response in cache
        # ======================================================
        cache.set(cache_key, data, self.CACHE_TIMEOUT)

        return Response(data, status=status.HTTP_200_OK)
