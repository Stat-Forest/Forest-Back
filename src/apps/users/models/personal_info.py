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
    positions = models.ForeignKey("users.Position", on_delete=models.PROTECT, related_name="personal_info")
    # ==================================================================================

    information = models.CharField(choices=Information.choices, help_text="Ma`lumoti")

    name_of_education_university = models.CharField(max_length=300,
                                                    help_text="oliy ta`lim muassasi nomi")
    finished_of_education_university = models.DateField(help_text="Oliy talim muassasi tugatgan yili")
    number_of_diploma = models.CharField(max_length=300)
    specialization = models.CharField(max_length=300)
    academic_of_degree = models.CharField(max_length=300)

    temporary_job = models.CharField(max_length=300, help_text="vaqtinchalik ish joyi")

    # =================== Here time of start and end Position
    appointed_time = models.CharField(max_length=300, help_text="lavozimga tayinlangan vaqti")
    completion_of_the_position_time = models.CharField(max_length=300, help_text="lavozimni tugallangan vaqti")

    # ============================ Addition Information of user ============================

    languages = models.CharField(max_length=350)
    countries_visited = models.CharField(max_length=350)
    family_members = models.PositiveSmallIntegerField()
    party_membership = models.CharField(max_length=350)
    deputy_member = models.CharField(max_length=350)
    state_awards = models.CharField(max_length=350)
    military_service = models.BooleanField()
    convicted = models.BooleanField(default=False, help_text="Sudlanganmi")
    resume = models.FileField(upload_to="resumes/%Y/%m/%d/")

    def __str__(self):
        return self.information

