from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.reports.models import StatementColumn
from apps.reports.serializers import StatementColumnTreeSerializer

@extend_schema(tags=["Statements"])
class StatementColumnTreeAPIView(generics.GenericAPIView):
    serializer_class = StatementColumnTreeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_plan']

    def get_queryset(self):
        statement_id = self.request.query_params.get('statement')

        qs = StatementColumn.objects.all()

        if statement_id:
            qs = qs.filter(statement_id=statement_id)

        return qs.select_related('statement', 'parent')

    def get(self, request, *args, **kwargs):
        all_columns = list(self.filter_queryset(self.get_queryset()))

        # Build a map of ID to object
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

        data = self.get_serializer(tree, many=True).data
        return Response(data)
