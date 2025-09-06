from django.core.management.base import BaseCommand
from apps.reports.models import Report, ReportItem, ReportItemInner, Statement, StatementColumn, ColumnPlant, Plant
from apps.general.models import Organization
from apps.reports.models import Deadline
import uuid


class Command(BaseCommand):
    help = "Create empty plant-based report structure for testing purpose."

    def add_arguments(self, parser):
        parser.add_argument("--statement", type=str, required=True, help="Statement name (e.g. Ko‘chat-ilovasi)")
        parser.add_argument("--organization", type=str, required=True, help="Organization UUID")
        parser.add_argument("--deadline", type=str, required=True, help="Deadline UUID")

    def handle(self, *args, **options):
        statement_name = options["statement"]
        organization_id = options["organization"]
        deadline_id = options["deadline"]

        try:
            statement = Statement.objects.get(name_uz=statement_name)
        except Statement.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Statement not found: {statement_name}"))
            return

        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Organization not found: {organization_id}"))
            return

        try:
            deadline = Deadline.objects.get(id=deadline_id)
        except Deadline.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Deadline not found: {deadline_id}"))
            return

        # Report yaratamiz
        report = Report.objects.create(
            id=uuid.uuid4(),
            organization=organization,
            deadline=deadline,
            statement=statement,
            status="saved",  # or whatever default
            is_report=True
        )

        self.stdout.write(self.style.SUCCESS(f"Report created: {report.id}"))

        # ColumnPlantlarni olib chiqamiz
        column_plants = ColumnPlant.objects.filter(column__statement=statement).select_related("column", "plant")

        items_map = {}  # (column_id) -> ReportItem

        for cp in column_plants:
            column_id = cp.column.id
            plant_id = cp.plant.id

            if column_id not in items_map:
                # Yangi ReportItem yaratamiz
                report_item = ReportItem.objects.create(
                    id=uuid.uuid4(),
                    report=report,
                    statement_column=cp.column
                )
                items_map[column_id] = report_item
            else:
                report_item = items_map[column_id]

            # Bo‘sh ReportItemInner yaratamiz
            ReportItemInner.objects.create(
                id=uuid.uuid4(),
                report_item=report_item,
                plant=cp.plant,
                value=None  # Yoki "" qilsang ham bo‘ladi
            )

        self.stdout.write(self.style.SUCCESS("All ReportItem and ReportItemInner created successfully."))
