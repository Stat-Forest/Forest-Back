from rest_framework import generics
from apps.reports.models import Plan
from apps.reports.serializers import PlanSerializer

class PlanCreateView(generics.CreateAPIView):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer