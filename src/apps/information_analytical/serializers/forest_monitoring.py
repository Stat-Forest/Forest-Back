from collections import defaultdict

from rest_framework import serializers

from apps.base.serializers import CustomSerializer
from apps.utils.translation import get_translated_field


def ordering_key(ordering: str):
    return [int(x) for x in ordering.split(".") if x.isdigit()]


from functools import lru_cache


class ResultBlockBuilder:
    @staticmethod
    def build_tree(columns, lang="uz"):
        """
        Ultra optimized version
        """
        # Dictionary yasash
        columns_by_id = {col.id: col for col in columns}
        columns_by_parent = defaultdict(list)

        for col in columns:
            columns_by_parent[col.parent_id].append(col)

        # Sort by ordering
        for parent_id in columns_by_parent:
            columns_by_parent[parent_id].sort(
                key=lambda c: [int(x) for x in c.ordering.split(".") if x.isdigit()]
            )

        leaf_paths = {}

        # Translation cache
        @lru_cache(maxsize=500)
        def get_title(col_id):
            col = columns_by_id.get(col_id)
            if not col:
                return ""
            return get_translated_field(col, "title", lang)

        # Recursive function
        def build_node(parent_id, current_path):
            result = {}
            for col in columns_by_parent.get(parent_id, []):
                if col.is_organization:
                    continue

                title = get_title(col.id)
                new_path = current_path + [title]

                if col.id in columns_by_parent:
                    result[title] = build_node(col.id, new_path)
                else:
                    result[title] = ""
                    leaf_paths[col.ordering] = new_path

            return result

        skeleton = build_node(None, [])
        return skeleton, leaf_paths


def set_by_path(root: dict, path: list[str], value):
    cur = root
    for key in path[:-1]:
        cur = cur.setdefault(key, {})
    cur[path[-1]] = "" if value is None else value



class MonitoringNodeSerializer(CustomSerializer):
    level = serializers.CharField()
    hudud = serializers.CharField()
    result = serializers.DictField()
    children = serializers.ListField(required=False, child=serializers.DictField())