from django.core.management.base import BaseCommand
from django.db import transaction
from apps.reports.models import Plan, Statement, StatementColumn
from apps.general.models import Organization
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = "Create plans for 'Yopiq ildiz yirik hajmli' statement for Sirdaryo organization"

    @transaction.atomic
    def handle(self, *args, **options):
        year = 2025
        statement = Statement.objects.filter(
            name="Yopiq ildiz yirik hajmli",
            period=PeriodChoices.YILLIK
        ).first()

        if not statement:
            self.stdout.write(self.style.ERROR("❌ Statement topilmadi."))
            return

        organization = Organization.objects.filter(name__icontains="sirdaryo").first()

        if not organization:
            self.stdout.write(self.style.ERROR("❌ Sirdaryo nomli organization topilmadi."))
            return

        # 1. Oddiy YILLIK reja ustunlarini olamiz
        reja_columns = StatementColumn.objects.filter(
            statement=statement,
            title="Reja",
            status_plan=StatementColumn.PlanStatus.YILLIK
        )

        total_value = 0
        total_created = 0

        for column in reja_columns:
            plan, created = Plan.objects.get_or_create(
                statement=statement,
                organization=organization,
                column=column,
                year=year,
                defaults={'plan_value': 20}
            )
            if created:
                total_created += 1
                total_value += 20
            else:
                total_value += plan.plan_value

        # 2. YILLIK_TOTAL reja uchun alohida ustunni olamiz
        total_column = StatementColumn.objects.filter(
            statement=statement,
            title="Reja",
            status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL
        ).first()

        if total_column:
            Plan.objects.update_or_create(
                statement=statement,
                organization=organization,
                column=total_column,
                year=year,
                defaults={'plan_value': total_value}
            )
            total_created += 1
        else:
            self.stdout.write(self.style.WARNING("⚠️ YILLIK_TOTAL ustuni topilmadi."))

        self.stdout.write(self.style.SUCCESS(f"✅ {total_created} ta plan yaratildi (shu jumladan YILLIK_TOTAL)."))
