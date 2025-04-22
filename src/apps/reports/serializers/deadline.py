from rest_framework import serializers
from apps.reports.models import Deadline

class DeadlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deadline
        fields = '__all__'