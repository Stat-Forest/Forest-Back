from rest_framework import serializers
from apps.reports.models import Report, ReportItem
from apps.reports.serializers.report_item import ReportItemSerializer


class ReportListSerializer(serializers.ModelSerializer):
    organization = serializers.StringRelatedField()
    deadline = serializers.StringRelatedField()
    statement = serializers.StringRelatedField()
    period = serializers.SerializerMethodField()

    def get_period(self, obj):
        return obj.statement.period

    class Meta:
        model = Report
        fields = ['id', 'organization', 'statement', 'deadline', 'period', 'status', 'created_at']


class ReportDetailSerializer(serializers.ModelSerializer):
    items = ReportItemSerializer(many=True)

    class Meta:
        model = Report
        fields = ['id', 'items']

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        instance = super().update(instance, validated_data)

        existing_items = {item.id: item for item in instance.items.all()}

        for item_data in items_data:
            item_id = item_data.get('id')
            if item_id and item_id in existing_items:
                item = existing_items.pop(item_id)
                for attr, value in item_data.items():
                    setattr(item, attr, value)
                item.save()
            else:
                ReportItem.objects.create(report=instance, **item_data)

        # Delete removed items
        for item in existing_items.values():
            item.delete()

        return instance
