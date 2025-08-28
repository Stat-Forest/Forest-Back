from rest_framework import serializers

from apps.reports.models import ColumnPlant


class ColumnPlantSerializer(serializers.ModelSerializer):
    column_title = serializers.CharField(source="column.title_uz", read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True)

    class Meta:
        model = ColumnPlant
        fields = ["id", "column", "column_title", "plant", "plant_name"]
