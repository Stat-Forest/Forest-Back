from rest_framework import serializers
from apps.reports.models import Organization


class OrganizationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'region']