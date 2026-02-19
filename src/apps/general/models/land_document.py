from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.general.models.organization import Organization


class LandDocument(models.Model):
    """
    Stores official land-related documents belonging to organizations.
    """

    class DocumentType(models.TextChoices):
        FARMON = 'farmon', _('Farmon')
        QAROR = 'qaror', _('Qaror')
        BUYRUQ = 'buyruq', _('Buyruq')
        NIZOM = 'nizom', _('Nizom')
        YORIQNOMA = 'yoriqnoma', _('Yo‘riqnoma')
        REGLAMENT = 'reglament', _('Reglament')
        ARIZA = 'ariza', _('Ariza')
        MALUMOTNOMA = 'malumotnoma', _('Ma’lumotnoma')
        XIZMAT_XATI = 'xizmat_xati', _('Xizmat xati')
        DALOLATNOMA = 'dalolatnoma', _('Dalolatnoma')
        BAYONNOMA = 'bayonnoma', _('Bayonnoma')
        ISHONCHNOMA = 'ishonchnoma', _('Ishonchnoma')
        TUSHUNTIRISH_XATI = 'tushuntirish_xati', _('Tushuntirish xati')
        TAVSIFNOMA = 'tavsifnoma', _('Tavsifnoma')
        OTHER = 'other', _('Boshqa')

    name = models.CharField(_("Document Name"), max_length=255)

    date = models.DateField(_("Document Date"))

    document_type = models.CharField(
        _("Document Type"),
        max_length=30,
        choices=DocumentType.choices
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="land_documents",
        verbose_name=_("Organization")
    )

    comment = models.TextField(_("Comment"), blank=True, null=True)

    file = models.FileField(
        _("Attached File"),
        upload_to='documents/land/',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Yer hujjati")
        verbose_name_plural = _("Yer hujjatlari")
        ordering = ['-date', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()})"

    # ======================================================
    # Model-level validation (security layer)
    # ======================================================
    def clean(self):
        super().clean()

        if not self.name.strip():
            raise ValidationError({
                "name": _("Document name cannot be empty.")
            })

        if not self.organization:
            raise ValidationError({
                "organization": _("Organization must be selected.")
            })

        if self.date > timezone.now().date():
            raise ValidationError({
                "date": _("Document date cannot be in the future.")
            })
