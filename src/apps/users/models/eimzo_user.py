from django.db import models

from apps.base.models import AbstractBaseModel


class DigitalSignatureProfile(AbstractBaseModel):
    user = models.OneToOneField(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="eimzo_profile"
    )
    organization_name = models.OneToOneField(
        "general.Organization",
        on_delete=models.PROTECT,
        verbose_name="organization name"
    )
    position = models.OneToOneField(
        "users.Position",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name="Position"
    )
    tin = models.CharField(  # JShShIR or INN
        max_length=14,
        unique=True,
        verbose_name="STIR/JSHSHIR"
    )
    certificate_serial_number = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="certificate number"
    )
    certificate_expiry = models.DateTimeField(
        verbose_name="certificate deadline"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tin
