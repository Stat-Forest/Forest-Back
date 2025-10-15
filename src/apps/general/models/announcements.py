from django.core.validators import MinValueValidator
from django.db import models
from apps.base.models import AbstractBaseModel


class Announcement(AbstractBaseModel):
    title = models.CharField(max_length=250)
    desc = models.TextField(max_length=5000)
    image = models.ImageField(upload_to='announcements/%y/%m/%d')
    lnk = models.URLField(max_length=200)
    ordering = models.SmallIntegerField(validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=False)

    from_time = models.DateTimeField()
    to_time = models.DateTimeField()

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "E'lon"
        verbose_name_plural = "E'lonlar"
