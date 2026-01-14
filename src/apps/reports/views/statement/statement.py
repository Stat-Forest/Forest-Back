from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.reports.models import Statement
from apps.reports.serializers.statement import StatementSerializer

@extend_schema(
    tags=["Statements"],
    parameters=[
        OpenApiParameter(name="lang", description="Language: uz, ru", required=False, type=str),
    ]
)
class StatementListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StatementSerializer

    def get_queryset(self):
        user = self.request.user

        qs = Statement.objects.filter(is_used=True)

        if user.statement:
            return qs.filter(
                id=user.statement.id,
                parent__isnull=True
            ).prefetch_related('children')

        return qs.filter(
            parent__isnull=True
        ).prefetch_related('children')