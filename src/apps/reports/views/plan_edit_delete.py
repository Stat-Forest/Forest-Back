from rest_framework import generics
from apps.reports.serializers import PlanSerializer
from drf_spectacular.utils import extend_schema
from apps.reports.models import Plan



@extend_schema(tags=["Plan"])
class PlanUpdateAPIView(generics.UpdateAPIView):
    queryset = Plan.objects.select_related('organization', 'column')
    serializer_class = PlanSerializer
    lookup_field = 'id'

@extend_schema(tags=["Plan"])
class PlanDeleteAPIView(generics.DestroyAPIView):
    queryset = Plan.objects.all()
    lookup_field = 'id'