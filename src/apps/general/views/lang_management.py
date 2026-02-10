# apps/general/views/land_management.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum

from apps.general.models import LandManagement
from apps.general.serializers.land_management import LandManagementItemSerializer


class LandManagementSummaryAPIView(APIView):

    def get(self, request):
        queryset = LandManagement.objects.all()

        total = queryset.aggregate(total=Sum('area'))['total'] or 0
        total = float(total.normalize()) if total else 0

        serializer = LandManagementItemSerializer(
            queryset,
            many=True,
            context={"request": request}  #
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
