from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.general.models.organization import Organization

class LandDocument(models.Model):
    class DocumentType(models.TextChoices):
        OWNERSHIP = 'ownership', _('Ownership Document')
        RENT = 'rent', _('Rent Agreement')
        CERTIFICATE = 'certificate', _('Certificate')
        OTHER = 'other', _('Other')

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
        verbose_name = _("Land Document")
        verbose_name_plural = _("Land Documents")
        ordering = ['-date', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()})"

    # ✅ Validation
    def clean(self):
        super().clean()

        if self.date > timezone.now().date():
            raise ValidationError({
                "date": _("The date cannot be in the future.")
            })

        if not self.name.strip():
            raise ValidationError({
                "name": _("Document name cannot be empty.")
            })

        if not self.organization:
            raise ValidationError({
                "organization": _("Organization must be selected.")
            })
