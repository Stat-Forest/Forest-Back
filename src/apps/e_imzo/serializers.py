from rest_framework import serializers

class EimzoLoginSerializer(serializers.Serializer):
    vo = serializers.JSONField(required=False)
    pkcs7 = serializers.CharField()

