from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class LandManagement(models.Model):
    name = models.CharField(_("Land Name"), max_length=255)

    area = models.DecimalField(
        _("Area (ga)"),
        max_digits=20,
        decimal_places=3,
        help_text=_("Maydon hajmi gektar bilan")
    )

    comment = models.TextField(_("Comment"), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Yer maydoni kiritish")
        verbose_name_plural = _("Yer maydonlari kiritish")
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.area is None:
            raise ValidationError({"area": _("Maydon majburiy.")})

        if self.area <= 0:
            raise ValidationError({"area": _("Maydon hajmi musbat bo‘lishi kerak.")})
