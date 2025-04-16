from django.db import models
from rest_framework.exceptions import ValidationError

from apps.base.models import AbstractBaseModel
from apps.utils.services import StatementChoices


class StaffReport(AbstractBaseModel):
    report = models.ForeignKey(
        'reports.Report',
        on_delete=models.CASCADE,
        related_name='reports',
        null=True,
        blank=True,
        limit_choices_to= {
            'statement': StatementChoices.HODIMLAR_HISOBI,
        }
    )
    # Workers
    all_workers = models.PositiveIntegerField(default=0)
    management_workers = models.PositiveIntegerField(default=0)
    expert_workers = models.PositiveIntegerField(default=0)
    production_workers = models.PositiveIntegerField(default=0)
    technical_workers = models.PositiveIntegerField(default=0)
    service_workers = models.PositiveIntegerField(default=0)
    workers = models.PositiveIntegerField(default=0)

    # Vacancies
    all_vacancies = models.PositiveIntegerField(default=0)
    management_vacancies = models.PositiveIntegerField(default=0)
    expert_vacancies = models.PositiveIntegerField(default=0)
    technical_vacancies = models.PositiveIntegerField(default=0)
    service_vacancies = models.PositiveIntegerField(default=0)
    vacancies = models.PositiveIntegerField(default=0)

    # Staff positions and education
    total_staff_positions = models.PositiveIntegerField(default=0)
    total_number_employed_staff = models.PositiveIntegerField(default=0)
    higher_education = models.PositiveIntegerField(default=0)
    secondary_education = models.PositiveIntegerField(default=0)
    general_education = models.PositiveIntegerField(default=0)

    # Gender and age
    females = models.PositiveIntegerField(default=0)
    males = models.PositiveIntegerField(default=0)
    girls = models.PositiveIntegerField(default=0)
    boys = models.PositiveIntegerField(default=0)
    girls_under_30 = models.PositiveIntegerField(default=0)
    boys_under_30 = models.PositiveIntegerField(default=0)

    # Other indicators
    retired_workers = models.PositiveIntegerField(default=0)
    academic_degrees = models.PositiveIntegerField(default=0)
    foreign_language_employees = models.PositiveIntegerField(default=0)
    educated_and_trained_abroad = models.PositiveIntegerField(default=0)
    total_number_new_jobs_created = models.PositiveIntegerField(default=0)
    permanent_workers = models.PositiveIntegerField(default=0)
    seasonal_workers = models.PositiveIntegerField(default=0)
    included_iron_book_women_list = models.PositiveIntegerField(default=0)
    from_low_income_families = models.PositiveIntegerField(default=0)
    based_home_based_work = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Staff Report"
        verbose_name_plural = "Staff Reports"

    def clean(self):
        super().clean()
        if self.report and self.report.statement != StatementChoices.HODIMLAR_HISOBI:
            raise ValidationError({'report': 'Faqat "Hodimlar hisobi" statementiga ega report tanlanishi mumkin.'})

    def __str__(self):
        return f"{self.report.organization} - {self.report.statement}"
