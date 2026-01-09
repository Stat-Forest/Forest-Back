from django.db import models
from django.utils.translation import gettext_lazy as _
from datetime import datetime


def handbook_upload_path(instance, filename):
    today = datetime.now()
    return f"handbooks/{today.strftime('%d/%m/%Y')}/{filename}"


class Handbook(models.Model):
    name = models.CharField(_("Handbook Name"), max_length=255)
    file = models.FileField(
        _("Attached File"),
        upload_to=handbook_upload_path,
        blank=True,
        null=True
    )
    is_seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Qo‘llanma")
        verbose_name_plural = _("Qo‘llanmalar")
        ordering = ['-created_at', 'name']

    def __str__(self):
        return self.name
