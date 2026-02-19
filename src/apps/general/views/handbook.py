from rest_framework import generics, permissions, filters
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from apps.general.models.handbook import Handbook
from apps.general.serializers.handbook import HandBookSerializer
from apps.logs.drf_mixins import DRFHistoryMixin


@extend_schema(tags=["Handbook"])
class HandbookListCreateView(DRFHistoryMixin, generics.ListCreateAPIView):
    """
    API endpoint for handbook documents.

    GET:
        Returns visible handbooks (is_seen=True)

    POST:
        Creates new handbook (authenticated users only)

    Security:
        - Accessible only for authenticated users

    Performance:
        - Uses caching to reduce database queries
        - Cache cleared automatically via signals
    """

    serializer_class = HandBookSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]

    search_fields = ["name"]
    ordering_fields = ["created_at"]

    CACHE_TIMEOUT = 60 * 60

    def get_queryset(self):
        """
        Returns handbook list using cache layer.
        """

        cache_key = "visible_handbooks"

        queryset = cache.get(cache_key)

        if queryset is None:
            queryset = (
                Handbook.objects
                .filter(is_seen=True)
                .order_by("-created_at")
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
