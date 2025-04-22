from django.core.cache import cache
from rest_framework.response import Response

from apps.reports.models import Organization
from apps.base.views import CustomListAPIView
from apps.general.serializers import OrganizationListSerializer

class OrganizationListAPIView(CustomListAPIView):
    serializer_class = OrganizationListSerializer
    CACHE_KEY = 'organization_list_cache'
    cache_timeout = 60 * 60

    def list(self, request, *args, **kwargs):
        cached_data = cache.get(self.CACHE_KEY)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        cache.set(self.CACHE_KEY, serializer.data, self.cache_timeout)
        return Response(serializer.data)

    def get_queryset(self):
        return Organization.objects.all()
