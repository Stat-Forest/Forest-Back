from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from apps.reports.models import PlanItem
from apps.reports.serializers.plan import PlanItemSerializer

from drf_spectacular.utils import extend_schema

# -----------------------------------------------------------------------------
# PlanItem Detail API
# -----------------------------------------------------------------------------
@extend_schema(tags=["PlanItem"])
class PlanItemDetailAPIView(generics.ListAPIView):
    queryset = PlanItem.objects.all()
    pagination_class = None
    serializer_class = PlanItemSerializer
    filter_backends = [DjangoFilterBackend]

    # nested lookuplar
    filterset_fields = {
        "plan__organization": ["exact"],
        "plan__statement": ["exact"],
        "plan__year": ["exact"],
        "column": ["exact"],
    }
