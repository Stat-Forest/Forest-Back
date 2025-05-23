from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.reports.models import Statement
from apps.reports.serializers import StatementSerializer


@extend_schema(tags=["Statements"])
class StatementListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cache_key = f"user_statements_{user.id}"
        data = cache.get(cache_key)

        if not data:
            if user.statement:
                queryset = Statement.objects.filter(id=user.statement.id).prefetch_related('children')
            else:
                queryset = Statement.objects.filter(parent__isnull=True).prefetch_related('children')

            serializer = StatementSerializer(queryset, many=True)
            data = serializer.data
            cache.set(cache_key, data, timeout=60 * 5)

        return Response(data)
