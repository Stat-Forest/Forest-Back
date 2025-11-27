from rest_framework import serializers
from apps.reports.models import Deadline


class DeadlineExpiredSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deadline
        fields = ("id", "submit_at", "deadline_at", "statement", "organizations")
