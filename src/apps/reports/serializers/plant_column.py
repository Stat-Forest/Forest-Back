from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.reports.models import Plant


class PlantSerializer(CustomModelSerializer):
    children = serializers.SerializerMethodField(read_only=True)
    parent_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Plant
        fields = [
            "id",
            "name",
            "parent",
            "parent_name",
            "children"
        ]

    def get_parent_name(self, obj):
        return obj.parent.name if obj.parent else None

    def get_children(self, obj):
        if obj.parent is None:
            children = obj.children.all()
            return [
                {
                    "id": child.id,
                    "name": child.name,
                    "parent": str(child.parent_id),
                    "parent_name": obj.name,
                    "children": []
                }
                for child in children
            ]
        return []