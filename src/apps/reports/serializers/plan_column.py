from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.reports.models import StatementColumn


class PlanColumnSerializer(CustomModelSerializer):
    parent = serializers.StringRelatedField()

    class Meta:
        model = StatementColumn
        fields = [
            "parent",
            "title",
            "ordering",
            "is_plane",
        ]