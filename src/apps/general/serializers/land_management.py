# apps/reports/serializers/land.py

from rest_framework import serializers
from apps.general.models import LandManagement


class LandManagementItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandManagement
        fields = ('name', 'area')
