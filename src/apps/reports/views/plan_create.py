from rest_framework import generics
from apps.reports.models import Plan, StatementColumn
from apps.reports.serializers import PlanSerializer

class PlanCreateView(generics.ListCreateAPIView):
    queryset = Plan.objects.select_related('organization', 'column')
    serializer_class = PlanSerializer
