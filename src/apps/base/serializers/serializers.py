from rest_framework import serializers

from src.apps.base.serializers.abstract_serializer import AbstractCustomSerializerMixin


class CustomSerializer(serializers.Serializer, AbstractCustomSerializerMixin):
    pass
