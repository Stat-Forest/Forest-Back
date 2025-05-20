from rest_framework import generics
from apps.reports.models import Plan
from apps.reports.serializers import PlanSerializer

class PlanListAPIView(generics.ListAPIView):
    queryset = Plan.objects.select_related('organization', 'column')
    serializer_class = PlanSerializer


class PlanCreateView(generics.CreateAPIView):
    queryset = Plan.objects.select_related('organization', 'column')
    serializer_class = PlanSerializer