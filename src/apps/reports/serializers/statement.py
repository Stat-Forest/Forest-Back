# serializers.py
from rest_framework import serializers
from apps.reports.models import Statement

class StatementChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Statement
        fields = ('id', 'name')

class StatementSerializer(serializers.ModelSerializer):
    children = StatementChildSerializer(many=True, read_only=True)

    class Meta:
        model = Statement
        fields = ('id', 'name', 'period','icon', 'parent', 'children')
