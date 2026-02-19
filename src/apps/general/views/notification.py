# ==============================
# views.py
# ==============================
from rest_framework import generics
from django.core.cache import cache
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.general.models import Notification
from apps.general.serializers import NotificationListSerializer


@extend_schema(
    tags=["Notification"],
    summary="List active notifications",
    description="Returns notifications from today onwards with translation support",
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Tilni tanlang: uz yoki ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
        ),
    ],
    responses={200: NotificationListSerializer(many=True)}
)
class NotificationListCreateAPIView(generics.ListAPIView):
    """
    GET:
        Returns list of active notifications (date >= today)
    Security:
        - Accessible to any user
    Performance:
        - Uses caching to reduce database queries
        - Cache automatically cleared via signals
    """

    serializer_class = NotificationListSerializer
    CACHE_TIMEOUT = 60 * 60

    def get_queryset(self):
        """
        Returns active notifications using cache layer.
        Cache key is language dependent to handle translations.
        """
        lang = self.request.query_params.get("lang", "uz")
        cache_key = f"notifications:{lang}"

        queryset = cache.get(cache_key)
        if queryset is None:
            # Filter notifications from today onwards
            today = now().date()
            queryset = Notification.objects.filter(date__gte=today).order_by("-date")
            cache.set(cache_key, queryset, self.CACHE_TIMEOUT)

        return queryset

    def get_serializer_context(self):
        """
        Pass 'lang' to serializer context for translated text.
        """
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        return context
