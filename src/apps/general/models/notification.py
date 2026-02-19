# ==============================
# models.py
# ==============================
from django.db import models
from apps.base.models import AbstractBaseModel


class Notification(AbstractBaseModel):
    """
    Stores notifications with date and text content.
    """

    date = models.DateField(
        help_text="The date when the notification is active"
    )
    text = models.TextField(
        max_length=1000,
        help_text="Notification text"
    )

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering = ["-date"]

    def __str__(self):
        # Display first 50 characters for admin or str representation
        return self.text[:50]
