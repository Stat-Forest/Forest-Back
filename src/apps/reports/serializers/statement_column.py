from rest_framework import serializers
from apps.reports.models import StatementColumn

class StatementColumnTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    statement = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StatementColumn
        fields = [
            'id', 'statement', 'title',
            'ordering', 'parent', 'status_plan',
            'is_organization','children'
        ]

    def get_children(self, obj):
        if hasattr(obj, 'children_list'):
            return StatementColumnTreeSerializer(obj.children_list, many=True).data
        return []
