from datetime import date
from datetime import datetime

from rest_framework import serializers
from apps.reports.models import Report, ReportItem
from apps.utils.services.choices import PeriodChoices


class ReportItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportItem
        fields = ['statement_column', 'value']


class ReportCreateSerializer(serializers.ModelSerializer):
    report_items = ReportItemCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Report
        fields = ['id', 'organization', 'deadline', 'report_items']

    def validate(self, attrs):
        organization = attrs.get('organization')
        deadline = attrs.get('deadline')
        statement = deadline.statement

        def get_week_of_month():
            today = datetime.now().date()
            first_day = today.replace(day=1)
            adjusted_dom = today.day + first_day.weekday()
            return (adjusted_dom - 1) // 7 + 1

        if not deadline.organizations.filter(id=organization.pk).exists():
            raise serializers.ValidationError({
                'organization': ['This organization is not allowed for the selected deadline.']
            })

        if deadline.statement.period == PeriodChoices.KUNLIK:
            if int(deadline.submit_at[-2::]) > date.today().day:
                raise serializers.ValidationError({
                    'submit_at': ['You can only submit before tomorrow.']
                })

        if deadline.statement.period == PeriodChoices.HAFTALIK:
            if int(deadline.submit_at[-1]) > get_week_of_month():
                raise serializers.ValidationError({
                    'submit_at': ['You can only submit before the next tomorrow.']
                })
        if deadline.statement.period == PeriodChoices.OYLIK:
            if int(deadline.submit_at[-2::]) > date.today().month:
                raise serializers.ValidationError({
                    'submit_at': ['You can only submit before next month.']
                })

        if deadline.statement.period == PeriodChoices.CHORAKLIK:
            if int(deadline.submit_at[-1]) == 1:
                if date.today().month in (1, 2):
                    raise serializers.ValidationError({
                        'submit_at': ['You can only create report after February.']
                    })
            if int(deadline.submit_at[-1]) == 2:
                if date.today().month in (1, 2, 3, 4, 5):
                    raise serializers.ValidationError({
                        'submit_at': ['You can only create report  after May.']
                    })

            if int(deadline.submit_at[-1]) == 3:
                if date.today().month in (1, 2, 3, 4, 5, 6, 7, 8):
                    raise serializers.ValidationError({
                        'submit_at': ['You can only create report after Avgust.']
                    })
            if int(deadline.submit_at[-1]) == 4:
                if date.today().month in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
                    raise serializers.ValidationError({
                        'submit_at': ['You can only create report after November.']
                    })

        if deadline.statement.period == PeriodChoices.YILLIK:
            if int(deadline.submit_at) > date.today().year:
                raise serializers.ValidationError({
                    'submit_at': ['You can only submit before the next year.']
                })

        if Report.objects.filter(
                organization=organization,
                statement=statement,
                deadline=deadline
        ).exists():
            raise serializers.ValidationError({
                'non_field_errors': ['This report already exists.']
            })

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('report_items')
        deadline = validated_data['deadline']
        validated_data['statement'] = deadline.statement
        report = Report.objects.create(**validated_data)

        for item_data in items_data:
            ReportItem.objects.create(report=report, **item_data)

        return report
