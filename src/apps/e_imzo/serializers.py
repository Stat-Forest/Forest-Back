from rest_framework import serializers

class EimzoLoginSerializer(serializers.Serializer):
    vo = serializers.JSONField()
    pkcs7 = serializers.CharField()
