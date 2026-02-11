# apps/general/views/land_management.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.general.models import LandManagement
from apps.general.serializers.land_management import LandManagementItemSerializer


class LandManagementSummaryAPIView(APIView):

    @extend_schema(
        summary="Yer maydonlari statistikasi",
        description="Yer turlari bo‘yicha umumiy maydon va ro‘yxat",
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
    def format_total(self, total, lang="uz"):
        from decimal import Decimal

        total = Decimal(total)

        if total >= Decimal("1000000"):
            result = total / Decimal("1000000")
            return f"{result.normalize()} {'mln' if lang == 'uz' else 'млн'}"

        elif total >= Decimal("1000"):
            result = total / Decimal("1000")
            return f"{result.normalize()} {'ming' if lang == 'uz' else 'тыс'}"

        return f"{total.normalize()}"

    def get(self, request):
        queryset = LandManagement.objects.all()
        total = queryset.aggregate(total=Sum('area'))['total'] or 0

        lang = request.GET.get("lang", "uz")

        serializer = LandManagementItemSerializer(
            queryset,
            many=True,
            context={"request": request, "lang": lang}
        )

        formatted_total = self.format_total(total, lang)

        title_map = {
            "uz": f"Jami {formatted_total} ga",
            "ru": f"Итого {formatted_total} га"
        }

        data = {
            "title": title_map.get(lang, title_map["uz"]),
            "items": serializer.data
        }

        return Response(data, status=status.HTTP_200_OK)

