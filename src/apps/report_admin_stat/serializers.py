# apps/report_admin_stat/chat_serializers.py
from rest_framework import serializers


class StatRowSerializer(serializers.Serializer):
    id        = serializers.UUIDField()
    name      = serializers.CharField()
    count     = serializers.IntegerField()
    saved     = serializers.IntegerField()
    sent      = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    accepted  = serializers.IntegerField()
    total     = serializers.IntegerField()


class FatherStatementStatSerializer(StatRowSerializer):
    children = StatRowSerializer(many=True)


class TotalsSerializer(serializers.Serializer):
    count     = serializers.IntegerField()
    saved     = serializers.IntegerField()
    sent      = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    accepted  = serializers.IntegerField()
    total     = serializers.IntegerField()


class StatementStatResponseSerializer(serializers.Serializer):
    data   = FatherStatementStatSerializer(many=True)
    totals = TotalsSerializer()