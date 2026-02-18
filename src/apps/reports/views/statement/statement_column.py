from django_filters.rest_framework import DjangoFilterBackend
from django.forms import widgets
from django.core.cache import cache

from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.response import Response

import django_filters

from apps.reports.serializers.statement.statement_column import (
    StatementColumnTreeSerializer
)
from apps.reports.models import Statement, StatementColumn
from apps.utils.translation import get_translated_field


CACHE_TIMEOUT = 60 * 60 * 24
CACHE_KEY_PREFIX = "statement_column_tree_v1:"


class StatementColumnFilter(django_filters.FilterSet):
    statement = django_filters.ModelChoiceFilter(
        queryset=Statement.objects.filter(parent__isnull=False)
    )

    is_user_input = django_filters.BooleanFilter(
        field_name="is_user_input",
        widget=widgets.Select(
            choices=[('', '---------'), (True, 'True'), (False, 'False')]
        )
    )

    class Meta:
        model = StatementColumn
        fields = ['statement', "is_user_input"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        lang = "uz"
        if self.request:
            lang = self.request.GET.get("lang", "uz").lower()

        self.filters['statement'].label_from_instance = (
            lambda obj: get_translated_field(obj, 'name', lang)
        )


def _register_cache_key(cache_key: str):
    """
    Yangi cache kalitini markaziy registry-ga qo'shamiz.
    Signal bu ro'yxat orqali barcha kalitlarni topadi va tozalaydi.
    """
    registry_key = f"{CACHE_KEY_PREFIX}__registry__"
    all_keys: set = cache.get(registry_key) or set()
    all_keys.add(cache_key)
    cache.set(registry_key, all_keys, timeout=CACHE_TIMEOUT)


@extend_schema(
    tags=["Statements"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Language: uz, ru",
            required=False,
            type=str
        ),
    ]
)
class StatementColumnTreeAPIView(generics.ListAPIView):
    serializer_class = StatementColumnTreeSerializer
    queryset = StatementColumn.objects.select_related('statement', 'parent')
    filter_backends = [DjangoFilterBackend]
    filterset_class = StatementColumnFilter

    def list(self, request, *args, **kwargs):
        lang = request.query_params.get("lang", "uz")
        statement_id = request.query_params.get("statement", "")
        is_user_input = request.query_params.get("is_user_input", "")

        cache_key = (
            f"{CACHE_KEY_PREFIX}"
            f"lang={lang}:"
            f"statement={statement_id}:"
            f"is_user_input={is_user_input}"
        )

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

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
            return sorted(
                columns,
                key=lambda c: [
                    int(p) for p in c.ordering.split('.')
                    if p.isdigit()
                ]
            )

        def sort_tree_recursive(nodes):
            nodes = sort_columns(nodes)
            for node in nodes:
                if hasattr(node, 'children_list'):
                    node.children_list = sort_tree_recursive(node.children_list)
            return nodes

        tree = sort_tree_recursive(tree)

        serializer = self.get_serializer(tree, many=True)
        data = list(serializer.data)  # ✅ ReturnList → oddiy list (cache uchun)

        cache.set(cache_key, data, timeout=CACHE_TIMEOUT)
        _register_cache_key(cache_key)

        return Response(data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        return context