from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser

from apps.base.models import AbstractBaseModel
from apps.users.manager import CustomUserManager
from apps.users.validations.passport_number_validate import validate_passport_number


class CustomUser(AbstractBaseModel, AbstractBaseUser, PermissionsMixin):
    class Gender(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")

    class Nation(models.TextChoices):
        UZBEK = "uz", _("Uzbek")
        RUSSIAN = "ru", _("Russian")
        TAJIK = "tj", _("Tajik")
        KAZAKH = "kz", _("Kazakh")
        KARAKALPAK = "krp", _("Karakalpak")
        TATAR = "tt", _("Tatar")
        KOREAN = "kr", _("Korean")
        UKRAINIAN = "ua", _("Ukrainian")
        TURKMEN = "tm", _("Turkmen")
        KYRGYZ = "kg", _("Kyrgyz")
        CHINESE = "cn", _("Chinese")
        JAPANESE = "jp", _("Japanese")
        OTHER = "ot", _("Other")

    
    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["first_name"]

    objects = CustomUserManager()

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

    def __str__(self):
        return self.email

