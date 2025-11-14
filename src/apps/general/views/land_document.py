from rest_framework import generics, permissions, filters
from apps.general.models.land_document import LandDocument
from apps.general.serializers.land_document import LandDocumentSerializer

from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    tags=["Land document"]
)
class LandDocumentListCreateView(generics.ListCreateAPIView):
    """
    GET -> list all LandDocuments
    POST -> create a new LandDocument
    """
    queryset = LandDocument.objects.select_related("organization").all().order_by("-date")
    serializer_class = LandDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "organization__name", "document_type"]
    ordering_fields = ["date", "created_at"]

    def perform_create(self, serializer):
        # If organization should come from user profile, adjust here.
        serializer.save()
