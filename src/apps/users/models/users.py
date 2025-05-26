from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser

from apps.base.models import AbstractBaseModel
from apps.users.manager import CustomUserManager
from apps.users.validations.passport_number_validate import validate_passport_number


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

    statement = models.ForeignKey("reports.Statement",
                                  limit_choices_to={"parent__isnull": True},
                                  on_delete=models.PROTECT,
                                  related_name="users",
                                  blank=True,
                                  null=True
                                  )

    organizations = models.ForeignKey("general.Organization",
                                      on_delete=models.PROTECT,
                                      related_name="users",
                                      blank=True,
                                      null=True
                                      )

    user_number = models.CharField(
        max_length=10,
        unique=True
    )

    role = models.CharField(Role.choices, max_length=50)

    gender = models.CharField(_("Gender"),
                              max_length=10,
                              choices=Gender.choices
                              )
    nationality = models.CharField(_("Nation"),
                                   choices=Nation.choices,
                                   max_length=10,
                                   default=Nation.UZBEK
                                   )

    is_disabled = models.BooleanField(default=False, help_text="Nogiron")

    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    father_name = models.CharField(max_length=250)
    email = models.EmailField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=13,
                                    blank=True,
                                    null=True,
                                    validators=[
                                        RegexValidator(
                                            regex=r"^\+998\d{9}$",
                                            message="Example: +998 XXXXXXXXX",
                                            code="uzb_phone_number_validation"
                                        )
                                    ])
    passport_number = models.CharField(max_length=9, validators=[validate_passport_number])

    date_of_birth = models.DateField(blank=True, null=True)
    date_of_place = models.CharField(max_length=250)
    address = models.CharField(max_length=250)

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
    
    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.SUPER_ADMIN
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.email
