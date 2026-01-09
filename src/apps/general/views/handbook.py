from rest_framework import generics, permissions, filters
from apps.general.models.handbook import Handbook
from apps.general.serializers.handbook import HandBookSerializer

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from apps.logs.drf_mixins import DRFHistoryMixin


@extend_schema(tags=["Handbook"])
class HandbookListCreateView(DRFHistoryMixin,generics.ListCreateAPIView):
    """
    GET -> list all LandDocuments
    POST -> create a new LandDocument
    """
    queryset = Handbook.objects.filter(is_seen=True).all().order_by("-created_at")
    serializer_class = HandBookSerializer
    permission_classes = [permissions.IsAuthenticated]

    # ADD FILTER AND SEARCH
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    search_fields = ["name"]
    ordering_fields = ["created_at"]

