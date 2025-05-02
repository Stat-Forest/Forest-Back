from django.core.cache import cache

from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.reports.models import Organization
from apps.base.views import CustomListAPIView
from apps.general.serializers import OrganizationListSerializer

@extend_schema(tags=["General"])
class OrganizationListAPIView(CustomListAPIView):
    serializer_class = OrganizationListSerializer
    filterset_fields = ['name', 'region']

    CACHE_TIMEOUT = 60 * 60

    def get_cache_key(self, request):
        """
        Generate cache key based on query params and pagination.
        This ensures the cache is specific to search filters and pages.
        """
        query_params = request.GET.urlencode() or "no_query"
        page = request.GET.get('page', '1')  # Handle pagination for caching
        return f"organization_list_cache:{query_params}:page={page}"

    def get_queryset(self):
        """
        Return all organizations from the database.
        Only fetched if no cached data exists.
        """
        return Organization.objects.all()

    def list(self, request, *args, **kwargs):
        """
        Check cache for pre-existing data or fetch fresh data from database.
        If no cache, fetch data and store in cache for future use.
        """
        cache_key = self.get_cache_key(request)
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, self.CACHE_TIMEOUT)
        return Response(data)
