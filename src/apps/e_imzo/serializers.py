from rest_framework import serializers


class EimzoLoginSerializer(serializers.Serializer):
    vo = serializers.JSONField(required=False, allow_null=True, default=dict)
    pkcs7 = serializers.CharField()
