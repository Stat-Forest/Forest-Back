from rest_framework import serializers

from apps.base.serializers import CustomSerializer


class AIRequestSerializer(CustomSerializer):
    question = serializers.CharField(max_length=2000, trim_whitespace=True)

    def validate_question(self, value: str) -> str:
        cleaned = " ".join((value or "").split()).strip()
        if not cleaned:
            raise serializers.ValidationError("Savol bo'sh bo'lmasligi kerak.")
        return cleaned