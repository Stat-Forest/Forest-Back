from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.core.cache import cache

from apps.general.models import Announcement
from apps.general.serializers import AnnouncementListSerializer


@extend_schema(
    tags=["Announcement"],
    parameters=[
        OpenApiParameter(
            name='lang',
            description='Select language (uz or ru)',
            required=False,
            type=str,
            enum=['uz', 'ru'],
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class AnnouncementListAPIView(generics.ListAPIView):
    """
    API endpoint that returns active announcements.

    Security:
    - Accessible only for authenticated users.
    - Language parameter is validated before usage.

    Performance:
    - Queryset is cached to reduce database load.
    - Cache is automatically cleared via signals when data changes.
    """

    serializer_class = AnnouncementListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['title']

    # Cache lifetime (1 hour)
    CACHE_TIMEOUT = 60 * 60

    def get_queryset(self):
        """
        Returns active announcements filtered by time range.
        Uses Redis cache to avoid repeated database queries.
        """

        # Defense-in-depth check (extra safety layer)
        if not self.request.user.is_authenticated:
            return Announcement.objects.none()

        now = timezone.now()

        # Cache key used to store active announcements
        cache_key = "active_announcements"

        # Try to fetch queryset from cache
        queryset = cache.get(cache_key)

        # If cache is empty, query database and store result
        if queryset is None:
            queryset = Announcement.objects.filter(
                from_time__lte=now,
                to_time__gte=now,
                is_active=True
            ).order_by('ordering')

            # Save queryset into cache
            cache.set(cache_key, queryset, self.CACHE_TIMEOUT)

        return queryset

    def get_serializer_context(self):
        """
        Adds validated language parameter into serializer context.
        Defaults to 'uz' if invalid or missing.
        """
        context = super().get_serializer_context()

        lang = self.request.query_params.get('lang', 'uz')
        context['lang'] = lang if lang in ['uz', 'ru'] else 'uz'

        return context
