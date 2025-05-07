from rest_framework import serializers
from apps.reports.models.statement_column import StatementColumn


class StatementColumnSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent = serializers.StringRelatedField()
    statement = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = StatementColumn
        fields = ['id', 'statement', 'title', 'ordering', 'children', 'parent']

    def get_children(self, obj):
        qs = obj.statementcolumn_set.all().order_by('ordering')
        return StatementColumnSerializer(qs, many=True).data

    def get_parent(self, obj):
        return 