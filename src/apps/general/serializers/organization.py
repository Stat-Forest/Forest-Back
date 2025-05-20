from rest_framework import serializers

from apps.general.models import Organization


class OrganizationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'region']