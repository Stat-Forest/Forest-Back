from rest_framework.generics import ListAPIView

from apps.reports.models import ColumnPlant
from apps.reports.serializers.plant import ColumnPlantSerializer

class ColumnPlantListAPIView(ListAPIView):
    serializer_class = ColumnPlantSerializer

    def get_queryset(self):
        queryset = ColumnPlant.objects.select_related("column", "plant")
        statement_id = self.request.query_params.get("statement_id")
        if statement_id:
            queryset = queryset.filter(column__statement_id=statement_id)
        return queryset
