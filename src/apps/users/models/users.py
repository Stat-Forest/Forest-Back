import random
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser

from django.core.exceptions import ValidationError
from apps.base.models import AbstractBaseModel
from apps.users.manager import CustomUserManager
from apps.users.validations.passport_number_validate import validate_passport_number, validate_jshshr
from apps.utils.services import RegionChoices
from apps.general.models import Organization


class CustomUser(AbstractBaseModel, AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", _("Super Admin")
        RAHBARIYAT = "rahbariyat", _("Rahbariyat")
        BOLIM_ADMIN = "bolim_admin", _("Bo`lim Admin")
        TASHKILOT_RAHBARI = "tashkilot_rahbari", _("Tashkilot rahbari")
        TASHKILOT_HODIMI = "tashkilot_hodimi", _("Tashkilot hodimi")
        HUDUDIY_BOSHQARMA = "hududiy_boshqarma", _("Hududiy boshqarma")

    class Gender(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")

    class Nation(models.TextChoices):
        UZBEK = "Uzbek"
        RUSSIAN = "Russian"
        TAJIK = "Tajik"
        KAZAKH = "Kazakh"
        KARAKALPAK = "Karakalpak"
        TATAR = "Tatar"
        KOREAN = "Korean"
        UKRAINIAN = "Ukrainian"
        TURKMEN = "Turkmen"
        KYRGYZ = "Kyrgyz"
        CHINESE = "Chinese"
        JAPANESE = "Japanese"
        OTHER = "Other"

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    statement = models.ForeignKey(
        "reports.Statement",
        limit_choices_to={"parent__isnull": True},
        on_delete=models.PROTECT,
        related_name="users",
        blank=True,
        null=True,
        help_text="Foydalanuvchining tegishli bo'lgan hisobot yo'nalishi"
    )

    organization = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
        related_name="users",
        blank=True,
        null=True,
        help_text="Foydalanuvchining ishlaydigan tashkiloti"
    )

    user_number = models.CharField(
        max_length=10,
        unique=True,
        help_text="Foydalanuvchiga biriktirilgan noyob raqam",
        blank=True
    )

    role = models.CharField(
        choices=Role.choices,
        max_length=50,
        help_text="Foydalanuvchining tizimdagi roli"
    )

    gender = models.CharField(
        _("Gender"),
        max_length=10,
        choices=Gender.choices,
        help_text="Foydalanuvchining jinsi"
    )

    nationality = models.CharField(
        _("Nation"),
        choices=Nation.choices,
        max_length=10,
        default=Nation.UZBEK,
        help_text="Foydalanuvchining millati"
    )

    is_disabled = models.BooleanField(
        default=False,
        help_text="Agar foydalanuvchi nogiron bo‘lsa belgilanadi"
    )

    first_name = models.CharField(
        max_length=250,
        help_text="Foydalanuvchining ismi"
    )

    last_name = models.CharField(
        max_length=250,
        help_text="Foydalanuvchining familiyasi"
    )

    father_name = models.CharField(
        max_length=250,
        help_text="Foydalanuvchining otasining ismi"
    )

    email = models.EmailField(
        max_length=150,
        unique=True,
        help_text="Foydalanuvchining elektron pochtasi"
    )

    phone_number = models.CharField(
        max_length=13,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\+998\d{9}$",
                message="Namuna: +998XXXXXXXXX",
                code="uzb_phone_number_validation"
            )
        ],
        help_text="Foydalanuvchining telefon raqami. Namuna: +998XXXXXXXXX"
    )

    passport_number = models.CharField(
        max_length=9,
        validators=[validate_passport_number],
        help_text="Foydalanuvchining pasport raqami (2 harf va 7 raqam)",
    )

    jshshr = models.CharField(
        max_length=14,
        validators=[validate_jshshr],
        help_text="Foydalanuvchining JSHSHR (14 xonali son)",
        blank=True
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text="Tug‘ilgan sana"
    )

    date_of_place = models.CharField(
        max_length=250,
        help_text="Tug‘ilgan joy"
    )

    address = models.CharField(
        max_length=250,
        help_text="Yashash manzili"
    )

    image = models.ImageField(
        upload_to="%Y/%m/%d",
        blank=True,
        null=True,
        help_text="Foydalanuvchining rasmi"
    )

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'), default=True, help_text=_(
            'Designates whether this user should be treated as active.'
            'Unselect this instead of deleting accounts.'
        ),
    )

    #===============================E-IMZO =======================
    pinfl = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        help_text="Foydalanuvchining PINFL raqami"
    )
    tin = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        help_text="Foydalanuvchining stir raqami"
    )

    full_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Foydalanuvchining to‘liq FISH (E-Imzodan kelgan `cn`)"
    )

    # ======  ROLE HUDUDIY BOSHQARMA =========
    region = models.CharField(
        max_length=50,
        choices=RegionChoices.choices,
        blank=True,
        null=True,
        help_text="Hududiy boshqarma foydalanuvchisi uchun region"
    )

    region_user_orgs = models.ManyToManyField(
        Organization,
        blank=True,
        related_name="regional_users",
        verbose_name="Biriktirilgan tashkilotlar",
        help_text="Hududiy boshqarma foydalanuvchisiga biriktiriladigan tashkilotlar"

    )
    last_activity = models.DateTimeField(null=True, blank=True)

    # def clean(self):
    #     super().clean()
    #
    #     if self.role == self.Role.HUDUDIY_BOSHQARMA:
    #         # 1. Region majburiy
    #         if not self.region:
    #             raise ValidationError({
    #                 "region": _("Hududiy boshqarma foydalanuvchisi uchun region majburiy.")
    #             })
    #
    #         # 2. Organization majburiy
    #         if not self.pk:
    #             # M2M save bo‘lishidan oldin tekshirib bo‘lmaydi
    #             return
    #
    #         orgs = self.region_user_orgs.all()
    #         if not orgs.exists():
    #             raise ValidationError({
    #                 "region_user_orgs": _("Kamida bitta tashkilot biriktirilishi shart.")
    #             })
    #
    #         # 3. Organization.region == user.region tekshiruvi
    #         invalid_orgs = orgs.exclude(region=self.region)
    #         if invalid_orgs.exists():
    #             raise ValidationError({
    #                 "region_user_orgs": _(
    #                     "Biriktirilgan tashkilotlar foydalanuvchi regioniga mos emas."
    #                 )
    #             })

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
    
    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.SUPER_ADMIN
        if not self.user_number:
            while True:
                rand_num = str(random.randint(100000, 999999))
                if not CustomUser.objects.filter(user_number=rand_num).exists():
                    self.user_number = rand_num
                    break
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.email
