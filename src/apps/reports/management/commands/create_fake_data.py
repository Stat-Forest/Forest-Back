from django.db import transaction
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.general.models import Organization
from apps.reports.models import Deadline, Report, ReportItem, StatementColumn
from apps.utils.services import StatementChoices, PeriodChoices, DAILY_STATEMENTS, WEEKLY_STATEMENTS, \
    MONTHLY_STATEMENTS, QUARTERLY_STATEMENTS, YEARLY_STATEMENTS

STATEMENT = StatementChoices.HODIMLAR_HISOBI

COLUMNS = [
    "all_workers", "management_workers", "expert_workers", "production_workers", "technical_workers", "service_workers", "workers",
    "all_vacancies", "management_vacancies", "expert_vacancies", "technical_vacancies", "service_vacancies", "workers_vacancies",
    "total_staff_positions", "total_number_employed_staff", "higher_education", "secondary_education", "general_education",
    "females", "males", "young_people","girls", "boys","retired_workers", "academic_degrees",
    "foreign_language_employees", "educated_and_trained_abroad", "total_number_new_jobs_created", "permanent_workers",
    "seasonal_workers","girls_under_30", "boys_under_30", "included_iron_book_women_list", "from_low_income_families", "based_home_based_work"
]

class Command(BaseCommand):
    help = "Create fake data for testing: Organizations, Deadlines, Report, ReportItems, StatementColumns."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("🚀 Starting fake data creation..."))

        with transaction.atomic():
            # 1. Create one Organization per region
            regions = [choice[0] for choice in Organization._meta.get_field('region').choices]
            organizations = [
                Organization(name=f"Organization in {region}", region=region)
                for region in regions
            ]
            organizations = Organization.objects.bulk_create(organizations)
            self.stdout.write(self.style.SUCCESS(f"✅ Created {len(organizations)} organizations (1 per region)."))

            # 2. Create Deadlines
            deadlines = []
            for statement, _ in StatementChoices.choices:
                deadline = Deadline.objects.create(
                    statement=statement,
                    period=random.choice([choice[0] for choice in PeriodChoices.choices]),
                    submit_at=timezone.now() + timedelta(days=random.randint(1, 30))
                )
                selected_orgs = random.sample(organizations, min(3, len(organizations)))
                deadline.organizations.set(selected_orgs)
                deadlines.append(deadline)
            self.stdout.write(self.style.SUCCESS(f"✅ Created Deadlines for all statement choices."))

            # 3. Create StatementColumns
            StatementColumn.objects.filter(statement=STATEMENT).delete()
            statement_columns = [
                StatementColumn(
                    statement=STATEMENT,
                    title=title.replace("_", " ").title(),
                    ordering=i + 1
                ) for i, title in enumerate(COLUMNS)
            ]
            StatementColumn.objects.bulk_create(statement_columns)
            statement_columns = list(StatementColumn.objects.filter(statement=STATEMENT).order_by("ordering"))
            self.stdout.write(self.style.SUCCESS(f"✅ Created {len(statement_columns)} StatementColumns."))

            # 4. Create 1 Report per Organization
            total_reports = 0
            total_items = 0
            for org in organizations:
                if STATEMENT in DAILY_STATEMENTS:
                    period = PeriodChoices.KUNLIK
                elif STATEMENT in WEEKLY_STATEMENTS:
                    period = PeriodChoices.HAFTALIK
                elif STATEMENT in MONTHLY_STATEMENTS:
                    period = PeriodChoices.OYLIK
                elif STATEMENT in QUARTERLY_STATEMENTS:
                    period = PeriodChoices.CHORAKLIK
                elif STATEMENT in YEARLY_STATEMENTS:
                    period = PeriodChoices.OYLIK

                report = Report.objects.create(
                    organization=org,
                    period=period,
                    statement=STATEMENT,
                    status=Report.StatusChoices.SAVED
                )
                report_items = [
                    ReportItem(
                        report=report,
                        statement_column=col,
                        value=random.randint(1, 100)
                    ) for col in statement_columns
                ]
                ReportItem.objects.bulk_create(report_items)
                total_reports += 1
                total_items += len(report_items)

            self.stdout.write(self.style.SUCCESS(f"✅ Created {total_reports} Reports with {total_items} ReportItems."))

        self.stdout.write(self.style.SUCCESS("🎉 Fake data creation completed successfully!"))
