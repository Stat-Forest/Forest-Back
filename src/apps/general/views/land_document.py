from rest_framework import generics, permissions, filters
from apps.general.models.land_document import LandDocument
from apps.general.serializers.land_document import LandDocumentSerializer

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from apps.logs.drf_mixins import DRFHistoryMixin


@extend_schema(tags=["Land document"])
class LandDocumentListCreateView(DRFHistoryMixin,generics.ListCreateAPIView):
    """
    GET -> list all LandDocuments
    POST -> create a new LandDocument
    """
    queryset = LandDocument.objects.select_related("organization").all().order_by("-date")
    serializer_class = LandDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    # ADD FILTER AND SEARCH
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    search_fields = ["name"]

    filterset_fields = ["organization"]

    ordering_fields = ["date", "created_at"]

