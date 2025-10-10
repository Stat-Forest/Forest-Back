from rest_framework import serializers

from apps.base.serializers import CustomSerializer
from apps.reports.models import ColumnPlant
from apps.reports.models.deadline import Deadline
from django.utils.translation import gettext_lazy as _


class PlantValueSerializer(CustomSerializer):
    plant = serializers.UUIDField()
    value = serializers.CharField(allow_blank=True, required=False)


class UniversalPlantReportItemSerializer(CustomSerializer):
    statement_column = serializers.UUIDField()
    inners = PlantValueSerializer(many=True)

    def validate(self, data):
        column_id = data["statement_column"]
        plant_ids = {item["plant"] for item in data["inners"]}
        allowed_plants = set(
            ColumnPlant.objects.filter(statement_column_id=column_id)
            .values_list("plant_id", flat=True)
        )
        invalid = plant_ids - allowed_plants
        if invalid:
            raise serializers.ValidationError(f"Ushbu plantlar columnga mos emas: {list(invalid)}")
        return data


class PlantReportInitSerializer(CustomSerializer):
    deadline_id = serializers.UUIDField()

    def validate_deadline_id(self, value):
        try:
            return Deadline.objects.get(id=value)
        except Deadline.DoesNotExist:
            raise serializers.ValidationError(_("Deadline topilmadi."))