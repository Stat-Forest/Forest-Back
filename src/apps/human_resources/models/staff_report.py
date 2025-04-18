from django.db import models
from django.conf import settings

from apps.base.models import AbstractBaseModel


class StaffReport(AbstractBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    organization = models.ForeignKey('general.Organization', on_delete=models.PROTECT)
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

    is_saved = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    is_accepted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.organization = self.user.organization
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Staff Report"
        verbose_name_plural = "Staff Reports"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.organization}"
