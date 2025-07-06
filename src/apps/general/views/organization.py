from django.core.cache import cache
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.general.models import Organization
from apps.base.views import CustomListAPIView
from apps.base.pagination import CustomPageNumberPagination
from apps.general.serializers import OrganizationListSerializer

@extend_schema(tags=["General"])
class OrganizationListAPIView(CustomListAPIView):
    serializer_class = OrganizationListSerializer
    pagination_class = None
    filterset_fields = ['name', 'region']
    CACHE_TIMEOUT = 1

    def get_cache_key(self, request):
        query_params = request.GET.urlencode() or "no_query"
        page = request.GET.get('page', '1')
        return f"organization_list_cache:{request.user.id}:{query_params}:page={page}"

    def get_queryset(self):
        user = self.request.user

        if hasattr(user, 'organization') and user.organization is not None:
            return Organization.objects.filter(id=user.organization.id)
        else:
            return Organization.objects.all()

    def list(self, request, *args, **kwargs):
        cache_key = self.get_cache_key(request)
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            cache.set(cache_key, paginated_response.data, self.CACHE_TIMEOUT)
            return paginated_response

        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        cache.set(cache_key, data, self.CACHE_TIMEOUT)
        return Response(data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang")
        if not lang:
            lang = "uz"
        context["lang"] = lang
        return context