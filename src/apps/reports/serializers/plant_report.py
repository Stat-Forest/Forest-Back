from rest_framework import serializers
from apps.reports.models.deadline import Deadline
from django.utils.translation import gettext_lazy as _


class PlantValueSerializer(serializers.Serializer):
    plant_id = serializers.UUIDField()
    plant_name = serializers.CharField()
    value = serializers.CharField(allow_blank=True, required=False)


class PlantColumnSerializer(serializers.Serializer):
    statement_column_id = serializers.UUIDField()
    statement_column_name = serializers.CharField()
    plant_values = PlantValueSerializer(many=True)


class PlantReportInitSerializer(serializers.Serializer):
    deadline_id = serializers.UUIDField()

    def validate_deadline_id(self, value):
        try:
            return Deadline.objects.get(id=value)
        except Deadline.DoesNotExist:
            raise serializers.ValidationError(_("Deadline topilmadi."))