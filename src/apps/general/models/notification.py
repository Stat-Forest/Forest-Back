from django.db import models
from apps.base.models import AbstractBaseModel

class Notification(AbstractBaseModel):
    date = models.DateField()
    text = models.TextField(max_length=1000)

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering = ["-date"]

    def __str__(self):
        return self.text[:50]  
