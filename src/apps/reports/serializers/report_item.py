import json
import uuid
from rest_framework import serializers
from apps.reports.models import ReportItem
from apps.general.models import Organization
from apps.utils.translation import get_lang_code, get_translated_field


class ReportItemSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = ReportItem
        fields = ['statement_column', 'value']

    def get_value(self, obj):
        lang = get_lang_code(self.context)
        plant_map = self.context.get('plant_map', {})
        raw = obj.value

        # 1. Plant-based JSON string
        if isinstance(raw, str):
            raw = raw.strip()
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    parsed = json.loads(raw.replace("'", '"'))  # optional fix for single quotes
                    if isinstance(parsed, list) and all("plant_id" in i and "value" in i for i in parsed):
                        return [
                            {
                                "plant_id": i["plant_id"],
                                "value": i["value"],
                                "plant_name": get_translated_field(
                                    obj=plant_map.get(i["plant_id"]),
                                    field="name",
                                    lang=lang
                                ) if plant_map.get(i["plant_id"]) else "Noma'lum o‘simlik"
                            }
                            for i in parsed
                        ]
                except json.JSONDecodeError:
                    pass

        # 2. UUID (organization ID)
        try:
            org_id = uuid.UUID(str(raw))
            org = Organization.objects.filter(id=org_id).first()
            if org:
                return get_translated_field(org, "name", lang)
        except (ValueError, TypeError):
            pass

        # 3. Plain string or number
        return raw


class ReportItemPlantValueSerializer(serializers.ModelSerializer):
    plant_id = serializers.SerializerMethodField()
    plant_name = serializers.SerializerMethodField()
    plant_type = serializers.SerializerMethodField()

    class Meta:
        model = ReportItem
        fields = ['plant_id', 'value', 'plant_name', 'plant_type']

    def get_plant_id(self, obj):
        return str(obj.plant_id) if obj.plant_id else None

    def get_plant_name(self, obj):
        lang = get_lang_code(self.context)
        if obj.plant:
            return get_translated_field(obj.plant, "name", lang)
        return None

    def get_plant_type(self, obj):
        if not obj.plant:
            return None
        if obj.plant.name == "Хўжалик ДЎХ":
            return "duh"
        elif obj.plant.parent_id:
            return "child"
        else:
            return "parent"
