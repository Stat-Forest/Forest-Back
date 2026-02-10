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
    def get(self, request):
        queryset = LandManagement.objects.all()

        total = queryset.aggregate(total=Sum('area'))['total'] or 0
        total = float(total.normalize()) if total else 0

        serializer = LandManagementItemSerializer(
            queryset,
            many=True,
            context={"request": request}
        )

        lang = request.GET.get("lang", "uz")

        title_map = {
            "uz": f"Jami {total} mln ga",
            "ru": f"Итого {total} млн га"
        }

        data = {
            "title": title_map.get(lang, title_map["uz"]),
            "items": serializer.data
        }

        return Response(data, status=status.HTTP_200_OK)
