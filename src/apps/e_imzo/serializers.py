# apps/e_imzo/serializers.py
from rest_framework import serializers


class EimzoLoginSerializer(serializers.Serializer):
    pkcs7 = serializers.CharField()
    vo = serializers.JSONField(required=False, allow_null=True, default=dict)
