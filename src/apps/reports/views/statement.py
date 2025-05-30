from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.reports.models import Statement
from apps.reports.serializers import StatementSerializer

@extend_schema(tags=["Statements"])
class StatementListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StatementSerializer

    def get_queryset(self):
        user = self.request.user
        if user.statement:
            return Statement.objects.filter(id=user.statement.id).prefetch_related('children')
        return Statement.objects.filter(parent__isnull=True).prefetch_related('children')
