from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum

from apps.general.models import LandManagement
from apps.general.serializers.land_management import LandManagementItemSerializer


class LandManagementSummaryAPIView(APIView):
    """
    Response:
    {
      "title": "Жами 7,1 млн га",
      "items": [
        {"name": "...", "area": 42.9},
        ...
      ]
    }
    """

    def get(self, request):
        queryset = LandManagement.objects.all()

        total = queryset.aggregate(total=Sum('area'))['total'] or 0

        serializer = LandManagementItemSerializer(queryset, many=True)

        data = {
            "title": f"Jami {total} mln ga",
            "items": serializer.data
        }

        return Response(data, status=status.HTTP_200_OK)
