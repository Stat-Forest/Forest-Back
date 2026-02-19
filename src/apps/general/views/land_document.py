from rest_framework import generics,filters
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from apps.general.models.land_document import LandDocument
from apps.general.serializers.land_document import LandDocumentSerializer
from apps.logs.drf_mixins import DRFHistoryMixin


@extend_schema(tags=["Land document"])
class LandDocumentListCreateView(DRFHistoryMixin, generics.ListCreateAPIView):
    """
    API endpoint for Land Documents.

    GET:
        Returns all land documents

    POST:
        Creates a new land document (authenticated users only)

    Security:
        - Accessible only for authenticated users

    Performance:
        - Uses Redis cache to reduce database queries
        - select_related prevents N+1 queries
        - Cache automatically cleared via Django signals
    """

    serializer_class = LandDocumentSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = ["name"]
    filterset_fields = ["organization"]
    ordering_fields = ["date", "created_at"]

    CACHE_TIMEOUT = 60 * 60

    def get_queryset(self):
        """
        Returns land documents using cache layer.
        """

        cache_key = "land_documents"

        queryset = cache.get(cache_key)

        if queryset is None:
            queryset = (
                LandDocument.objects
                .select_related("organization")
                .all()
                .order_by("-date")
            )

            cache.set(cache_key, queryset, self.CACHE_TIMEOUT)

        return queryset

    def get_serializer_context(self):
        """
        Adds request context for absolute file URL generation.
        """
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
