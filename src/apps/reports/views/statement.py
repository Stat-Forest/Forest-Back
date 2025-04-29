from rest_framework import generics

from apps.reports.models import Statement
from apps.reports.serializers import StatementSerializer

class StatementListAPIView(generics.ListAPIView):
    queryset = Statement.objects.filter(parent__isnull=True).prefetch_related('children')
    serializer_class = StatementSerializer
