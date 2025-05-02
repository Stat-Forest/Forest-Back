from drf_spectacular.utils import extend_schema

from apps.base.views import CustomListAPIView
from apps.reports.models import StatementColumn
from apps.reports.serializers import StatementColumnListSerializer


@extend_schema(tags=["Statements"])
class StatementColumnListAPIView(CustomListAPIView):
    queryset = StatementColumn.objects.all()
    serializer_class = StatementColumnListSerializer
    filterset_fields = ('statement',)
