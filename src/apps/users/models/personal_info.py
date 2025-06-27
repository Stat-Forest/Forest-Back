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
    positions = models.ForeignKey(
        "users.Position",
        on_delete=models.PROTECT,
        related_name="personal_info",
        help_text="Joriy egallayotgan lavozimingiz"
    )
    # ==================================================================================

    information = models.CharField(
        choices=Information.choices,
        help_text="Ma'lumotingizni tanlang"
    )

    name_of_education_university = models.CharField(
        max_length=300,
        help_text="Oliy ta'lim muassasasi nomi"
    )
    finished_of_education_university = models.DateField(
        help_text="Oliy ta'lim muassasasini tugatgan yilingiz"
    )
    number_of_diploma = models.CharField(
        max_length=300,
        help_text="Diplom raqamingiz"
    )
    specialization = models.CharField(
        max_length=300,
        help_text="Mutaxassisligingiz"
    )
    academic_of_degree = models.CharField(
        max_length=300,
        help_text="Akademik darajangiz (agar mavjud bo‘lsa)"
    )

    temporary_job = models.CharField(
        max_length=300,
        help_text="Vaqtinchalik ish joyi (agar mavjud bo‘lsa)"
    )

    appointed_time = models.CharField(
        max_length=300,
        help_text="Lavozimga tayinlangan vaqt (sana formatida)"
    )
    completion_of_the_position_time = models.CharField(
        max_length=300,
        help_text="Lavozimni tugallangan vaqt (sana formatida)"
    )

    # ============================ Addition Information of user ============================

    languages = models.CharField(
        max_length=350,
        help_text="Qanday tillarni bilasiz (vergul bilan ajrating)"
    )
    countries_visited = models.CharField(
        max_length=350,
        help_text="Qaysi davlatlarda bo‘lgansiz (vergul bilan ajrating)"
    )
    family_members = models.PositiveSmallIntegerField(
        help_text="Oila a'zolari soni"
    )
    party_membership = models.CharField(
        max_length=350,
        help_text="Partiyaviyligingiz (agar mavjud bo‘lsa)"
    )
    deputy_member = models.CharField(
        max_length=350,
        help_text="Deputat a'zoligi (agar mavjud bo‘lsa)"
    )
    state_awards = models.CharField(
        max_length=350,
        help_text="Davlat mukofotlari (agar mavjud bo‘lsa)"
    )
    military_service = models.BooleanField(
        help_text="Harbiy xizmatni o‘taganmisiz?"
    )
    convicted = models.BooleanField(
        default=False,
        help_text="Sudlanganmisiz?"
    )
    resume = models.FileField(
        upload_to="resumes/%Y/%m/%d/",
        help_text="Rezyume faylini yuklang (PDF yoki DOC formatda)"
    )

    def __str__(self):
        return self.information

