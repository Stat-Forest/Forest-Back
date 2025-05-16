from datetime import date
from datetime import datetime

from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.general.models import Organization
from apps.reports.models import Report, ReportItem, StatementColumn, Plan
from apps.utils.services.choices import PeriodChoices
from apps.base.exceptions.exception_files import CustomExceptionError


class ReportItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportItem
        fields = ['statement_column', 'value']


class ReportCreateSerializer(serializers.ModelSerializer):
    report_items = ReportItemCreateSerializer(many=True, write_only=True)
    CHACHE_KEY = f'report_organization'
    class Meta:
        model = Report
        fields = ['id','deadline', 'report_items']

    def validate(self, attrs):
        # organization = attrs.get('organization')
        report_items = attrs.get('report_items')
        deadline = attrs.get('deadline')
        user = self.context['request'].user
        statement = deadline.statement




        all_organization = []
        for item in report_items:
            if StatementColumn.objects.filter(statement_id=item['statement_column']).is_organization  == True:
                if (not Organization.objects.filter(organization_id=item['value']).exists()
                        or
                    item['value'] not in user.organizations.values_list('id',flat=True)):
                    raise CustomExceptionError(
                        code = 400,
                        detail= _('Invalid organization.')
                    )

                else:
                    all_organization.append(item['value'])

            if StatementColumn.objects.filter(statement_id=item['statement_column']).is_plan == True:
                if not Plan.objects.filter(plan_id=item['value'],column_id=item['statement_column']).exists():
                    raise CustomExceptionError(
                        code = 400,
                        detail= _('Invalid plan.')
                    )
            if (StatementColumn.objects.filter(statement_id=item['statement_column']).is_organization  == False
                and
                StatementColumn.objects.filter(statement_id=item['statement_column']).is_plan == False):

                if item['value'].isdigit() is not True:
                    raise CustomExceptionError(
                        code = 400,
                        detail= _('Invalid number.')
                    )
        if len(set(all_organization)) != 1:
            raise CustomExceptionError(
                code = 400,
                detail= _('Invalid organizations.')
            )
        cache.set(self.CHACHE_KEY, all_organization[0])
        del all_organization[0]

        def get_week_of_month():
            today = datetime.now().date()
            first_day = today.replace(day=1)
            adjusted_dom = today.day + first_day.weekday()
            return (adjusted_dom - 1) // 7 + 1

        # Checking if organization is allowed for the selected deadline
        if not deadline.organizations.filter(id=cache.get(self.CHACHE_KEY)).exists():
            raise CustomExceptionError(
                code=400,
                detail={
                    'organization': ['This organization is not allowed for the selected deadline.']
                }
            )

        # Validate based on period types (daily, weekly, monthly, etc.)
        if deadline.statement.period == PeriodChoices.KUNLIK:
            if int(deadline.submit_at[-2::]) > date.today().day:
                raise CustomExceptionError(
                    code=400,
                    detail={
                        'submit_at': ['You can only submit before tomorrow.']
                    }
                )

        if deadline.statement.period == PeriodChoices.HAFTALIK:
            if int(deadline.submit_at[-1]) > get_week_of_month():
                raise CustomExceptionError(
                    code=400,
                    detail={
                        'submit_at': ['You can only submit before the next tomorrow.']
                    }
                )

        if deadline.statement.period == PeriodChoices.OYLIK:
            if int(deadline.submit_at[-2::]) > date.today().month:
                raise CustomExceptionError(
                    code=400,
                    detail={
                        'submit_at': ['You can only submit before next month.']
                    }
                )

        if deadline.statement.period == PeriodChoices.CHORAKLIK:
            if int(deadline.submit_at[-1]) == 1:
                if date.today().month in (1, 2):
                    raise CustomExceptionError(
                        code=400,
                        detail={
                            'submit_at': ['You can only create report after February.']
                        }
                    )
            if int(deadline.submit_at[-1]) == 2:
                if date.today().month in (1, 2, 3, 4, 5):
                    raise CustomExceptionError(
                        code=400,
                        detail={
                            'submit_at': ['You can only create report after May.']
                        }
                    )

            if int(deadline.submit_at[-1]) == 3:
                if date.today().month in (1, 2, 3, 4, 5, 6, 7, 8):
                    raise CustomExceptionError(
                        code=400,
                        detail={
                            'submit_at': ['You can only create report after August.']
                        }
                    )
            if int(deadline.submit_at[-1]) == 4:
                if date.today().month in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
                    raise CustomExceptionError(
                        code=400,
                        detail={
                            'submit_at': ['You can only create report after November.']
                        }
                    )

        if deadline.statement.period == PeriodChoices.YILLIK:
            if int(deadline.submit_at) > date.today().year:
                raise CustomExceptionError(
                    code=400,
                    detail={
                        'submit_at': ['You can only submit before the next year.']
                    }
                )

        # Check if report already exists for the given organization, statement, and deadline
        if Report.objects.filter(
                organization=cache.get(self.CHACHE_KEY),
                statement=statement,
                deadline=deadline
        ).exists():
            raise CustomExceptionError(
                code=400,
                detail={
                    'non_field_errors': ['This report already exists.']
                }
            )

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('report_items')
        deadline = validated_data['deadline']
        validated_data['statement'] = deadline.statement
        validated_data['organization'] = cache.get(self.CHACHE_KEY)
        cache.get(self.CHACHE_KEY).delete()

        report = Report.objects.create(**validated_data)

        for item_data in items_data:
            ReportItem.objects.create(report=report, **item_data)

        return report
