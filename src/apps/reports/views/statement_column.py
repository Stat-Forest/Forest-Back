# views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from apps.reports.models import StatementColumn
from apps.reports.serializers import StatementColumnTreeSerializer
# filters.py
import django_filters
from apps.reports.models import Statement, StatementColumn


class StatementColumnFilter(django_filters.FilterSet):
    statement = django_filters.ModelChoiceFilter(
        queryset=Statement.objects.filter(parent__isnull=False)
    )

    class Meta:
        model = StatementColumn
        fields = ['statement']



@extend_schema(tags=["Statements"])
class StatementColumnTreeAPIView(generics.ListAPIView):
    serializer_class = StatementColumnTreeSerializer
    queryset = StatementColumn.objects.select_related('statement', 'parent')
    filter_backends = [DjangoFilterBackend]
    filterset_class = StatementColumnFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        all_columns = list(queryset)

        column_map = {col.id: col for col in all_columns}
        for col in all_columns:
            col.children_list = []

        tree = []
        for col in all_columns:
            if col.parent_id:
                parent = column_map.get(col.parent_id)
                if parent:
                    parent.children_list.append(col)
            else:
                tree.append(col)

        def sort_columns(columns):
            return sorted(columns, key=lambda c: [int(p) for p in c.ordering.split('.') if p.isdigit()])

        def sort_tree_recursive(nodes):
            nodes = sort_columns(nodes)
            for node in nodes:
                if hasattr(node, 'children_list'):
                    node.children_list = sort_tree_recursive(node.children_list)
            return nodes

        tree = sort_tree_recursive(tree)
        serializer = self.get_serializer(tree, many=True)
        return Response(serializer.data)
