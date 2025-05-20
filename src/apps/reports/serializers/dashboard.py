from rest_framework import serializers

class DashboardStatSerializer(serializers.Serializer):
    sent_reports = serializers.IntegerField()
    returned_reports = serializers.IntegerField()
    accepted_reports = serializers.IntegerField()
    draft_reports = serializers.IntegerField()
    responsible_users = serializers.IntegerField()
    deadlines = serializers.IntegerField()
