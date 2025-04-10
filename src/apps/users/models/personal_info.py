from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel


class PersonalInfo(AbstractBaseModel):
    class Information(models.TextChoices):
        Higher = "higher", _("Higher")
        Middle = "middle", _("Middle")
        MiddleSpecial = "middle special", _("Middle Special")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="personal_info"
    )

    # ======================== Tashkilot nomi va Lavozimi ==============================
    organizations = models.ForeignKey("users.Organization", on_delete=models.PROTECT, related_name="personal_info")
    positions = models.ForeignKey("users.Position", on_delete=models.PROTECT, related_name="personal_info")
    # ==================================================================================

    information = models.CharField(choices=Information.choices, blank=True, null=True, help_text="Ma`lumoti")

    name_of_education_university = models.CharField(max_length=300, blank=True, null=True,
                                                    help_text="oliy ta`lim muassasi nomi")
    finished_of_education_university = models.DateField(help_text="Oliy talim muassasi tugatgan yili", blank=True, null=True)
    number_of_diploma = models.CharField(max_length=300, blank=True, null=True)
    specialization = models.CharField(max_length=300, blank=True, null=True)
    academic_of_degree = models.CharField(max_length=300, blank=True, null=True)

    temporary_job = models.CharField(max_length=300, help_text="vaqtinchalik ish joyi", blank=True, null=True)

    # =================== Here time of start and end Position
    appointed_time = models.CharField(max_length=300, help_text="lavozimga tayinlangan vaqti")
    completion_of_the_position_time = models.CharField(max_length=300, help_text="lavozimni tugallangan vaqti")

    # ============================ Addition Information of user ============================

    languages = models.CharField(max_length=350, blank=True, null=True)
    countries_visited = models.CharField(max_length=350, blank=True, null=True)
    family_members = models.PositiveSmallIntegerField(blank=True, null=True)
    party_membership = models.CharField(max_length=350, blank=True, null=True)
    deputy_member = models.CharField(max_length=350, blank=True, null=True)
    state_awards = models.CharField(max_length=350, blank=True, null=True)
    military_service = models.BooleanField(blank=True, null=True)
    convicted = models.BooleanField(default=False, help_text="Sudlanganmi")
    resume = models.FileField(upload_to="resumes/%Y/%m/%d/", blank=True, null=True)

    def __str__(self):
        return self.information

