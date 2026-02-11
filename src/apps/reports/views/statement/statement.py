from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.core.cache import cache
from django.db.models import Prefetch

from apps.reports.models import Statement
from apps.reports.serializers.statement import StatementSerializer
from apps.reports.views.statement.cache_keys import get_statement_list_cache_key


@extend_schema(
    tags=["Statements"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Language: uz, ru",
            required=False,
            type=str,
            default="uz"
        ),
    ],
    description="Get list of statements with alphabetical ordering and caching"
)
class StatementListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StatementSerializer

    def get_queryset(self):
        """
        Optimized queryset with prefetch_related to avoid N+1 queries
        """
        user = self.request.user

        # Base queryset with optimization
        base_qs = Statement.objects.filter(
            is_used=True,
            parent__isnull=True
        ).prefetch_related(
            Prefetch(
                'children',
                queryset=Statement.objects.filter(is_used=True).order_by('name')
            )
        ).order_by('name')

        # Agar user'ning o'ziga tegishli statement bo'lsa
        if hasattr(user, 'statement') and user.statement:
            return base_qs.filter(id=user.statement.id)

        return base_qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        return context

    def list(self, request, *args, **kwargs):
        user = request.user
        lang = request.query_params.get("lang", "uz")

        # Cache key generation
        user_statement_id = user.statement.id if hasattr(user, 'statement') and user.statement else None
        cache_key = get_statement_list_cache_key(user_statement_id, lang)

        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        # Cache miss - fetch from database
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # Alfabetga qarab saralash (translated name bo'yicha, case-insensitive)
        data = sorted(data, key=lambda x: x['name'].lower())

        # Cache for 24 hours
        # Statementlar kam o'zgaradi, shuning uchun uzoq vaqt saqlash mumkin
        cache.set(cache_key, data, timeout=60 * 60 * 24)

        return Response(data)