from django.core.management.base import BaseCommand
from django.db import transaction

from apps.reports.models import Statement, StatementColumn
from apps.reports.models.statement_column import StatementColumn as SC
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = 'Creates default Statement and StatementColumn data'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            urmon_management = Statement.objects.create(
                name="O'rmon kadastri,ijara",
                parent=None
            )
            land_management = Statement.objects.create(
                name="Yer o'zlashtirish",
                parent=urmon_management,
                period=PeriodChoices.OYLIK,
            )

            land_1 = StatementColumn.objects.create(
                statement=land_management,
                parent=None,
                title="1-ilova",
                ordering="1"
            )
            land_info = StatementColumn.objects.create(
                statement=land_management,
                parent=land_1,
                title="2025 yilda foydalanishga kiritiladigan o‘rmon fondi yerlari maydoni to‘g‘risida ma’lumot",
                ordering="1.1"
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=land_info,
                title="Tashkilot nami",
                ordering="1.1.1",
                is_organization=True
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=land_info,
                title="Reja",
                ordering="1.1.2",
                status_plan=SC.PlanStatus.YILLIK
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=land_info,
                title="Amalda",
                ordering="1.1.3",
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=land_info,
                title="Shundan",
                ordering="1.1.4",
            )
