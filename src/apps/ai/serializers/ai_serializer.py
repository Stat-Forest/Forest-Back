from rest_framework import serializers

from apps.base.serializers import CustomSerializer


class AIRequestSerializer(CustomSerializer):
    question = serializers.CharField(max_length=2000)