from django.core.management.base import BaseCommand
from django.db import transaction
from apps.general.models import Organization
from apps.reports.models import Statement, Deadline, StatementColumn, Report, ReportItem
from apps.utils.services import RegionChoices, PeriodChoices
import random


class Command(BaseCommand):
    help = 'Seeds the database with test data for organizations, reports, deadlines, and more'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("🚧 Seeding started..."))

        try:
            with transaction.atomic():
                # 1. Create 13 organizations
                organizations = []
                for region in RegionChoices.values:
                    org, _ = Organization.objects.get_or_create(
                        name=f"{region.title()} Organization",
                        region=region
                    )
                    organizations.append(org)

                # 2. Create parent statements
                parent_titles = [
                    "Inson resurslarini boshqarish",
                    "Moliya-iqsisod va bugaltiriya",
                    "Urmon barpo qilish",
                    "Urmon kadestri-ijoara",
                    "Urmonlardan qoshimcha foydalanish",
                    "Urmonlarni muhofaza qilish"
                ]
                parents = []
                for title in parent_titles:
                    stmt, _ = Statement.objects.get_or_create(name=title, parent=None)
                    parents.append(stmt)

                # 3. Create child statement under 'Inson resurslarini boshqarish'
                hr_parent = Statement.objects.get(name="Inson resurslarini boshqarish")
                hodimlar_hisobi, _ = Statement.objects.get_or_create(
                    name="Hodimlar hisobi",
                    parent=hr_parent,
                    period=PeriodChoices.CHORAKLIK
                )

                # 4. Create 3 deadlines for that child statement
                quarters = ['2025-Q1', '2025-Q2', '2025-Q3']
                deadlines = []
                for q in quarters:
                    deadline, _ = Deadline.objects.get_or_create(
                        statement=hodimlar_hisobi,
                        submit_at=q
                    )
                    deadline.organizations.set(organizations)
                    deadlines.append(deadline)

                # 5. Create statement columns
                COLUMNS = [
                    "all_workers", "management_workers", "expert_workers", "production_workers", "technical_workers", "service_workers", "workers",
                    "all_vacancies", "management_vacancies", "expert_vacancies", "technical_vacancies", "service_vacancies", "workers_vacancies",
                    "total_staff_positions", "total_number_employed_staff", "higher_education", "secondary_education", "general_education",
                    "females", "males", "young_people", "girls", "boys", "retired_workers", "academic_degrees",
                    "foreign_language_employees", "educated_and_trained_abroad", "total_number_new_jobs_created", "permanent_workers",
                    "seasonal_workers", "girls_under_30", "boys_under_30", "included_iron_book_women_list", "from_low_income_families", "based_home_based_work"
                ]
                columns = []
                for idx, title in enumerate(COLUMNS):
                    col, _ = StatementColumn.objects.get_or_create(
                        statement=hodimlar_hisobi,
                        title=title,
                        ordering=idx + 1
                    )
                    columns.append(col)

                # 6. Create 13 reports and related report items
                for org in organizations:
                    report, _ = Report.objects.get_or_create(
                        organization=org,
                        statement=hodimlar_hisobi,
                        deadline=deadlines[0],  # 2025-Q1
                        defaults={"status": Report.StatusChoices.SAVED}
                    )
                    for col in columns:
                        ReportItem.objects.get_or_create(
                            report=report,
                            statement_column=col,
                            defaults={"value": random.randint(1, 100)}
                        )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Seeding failed: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("✅ Seeding completed successfully!"))
