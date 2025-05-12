from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.reports.models import StatementColumn
from apps.reports.serializers import StatementColumnTreeSerializer
from django.db.models import Prefetch

@extend_schema(tags=["Statements"])
class StatementColumnTreeAPIView(APIView):
    def get(self, request, *args, **kwargs):
        statement_id = request.query_params.get('statement')

        qs = StatementColumn.objects.all()

        if statement_id:
            qs = qs.filter(statement_id=statement_id)

        qs = qs.select_related('statement', 'parent')

        all_columns = list(qs)

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

        data = StatementColumnTreeSerializer(tree, many=True).data
        return Response(data)
