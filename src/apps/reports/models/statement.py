from django.db import models
from apps.utils.services import PeriodChoices
from apps.base.models import AbstractBaseModel


class StatementManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

    def get_active_parents(self):
        """Get active parent statements with optimized query"""
        return self.filter(
            parent__isnull=True,
            is_used=True
        ).select_related().prefetch_related(
            models.Prefetch(
                'children',
                queryset=Statement.objects.filter(is_used=True).order_by('name')
            )
        ).order_by('name')


class Statement(AbstractBaseModel):
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='children',
        limit_choices_to={'parent__isnull': True},
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=100, unique=True, db_index=True)
    period = models.CharField(
        max_length=100,
        choices=PeriodChoices.choices,
        blank=True,
        null=True,
    )
    icon = models.FileField(
        upload_to='statements/icons/%Y/%m/%d/',
        blank=True,
        null=True,
    )
    use_plant_plan = models.BooleanField(default=False)
    is_used = models.BooleanField(default=True, db_index=True)

    calculate_expression = models.TextField(
        blank=True,
        null=True,
        help_text=(
            "Bittali formulalarga"
            "column('1.1.5') / column('1.1.4') * 100 = column('1.1.6')"
            "Bir nechta formulalar uchun har birini alohida qatorga yozing.<br>"
            "Masalan:<br>"
            "column('1.1.5') / column('1.1.4') * 100 = column('1.1.6')<br>"
            "column('1.2.5') / column('1.2.4') * 100 = column('1.2.6')<br>"
            "column('1.3.5') / column('1.3.4') * 100 = column('1.3.6')"
        )
    )

    objects = StatementManager()

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new and hasattr(self, "name_uz") and self.name_uz:
            if not hasattr(self, "name_ru") or not self.name_ru:
                self.name_ru = self.name_uz
        super().save(*args, **kwargs)

    def natural_key(self):
        return (self.name,)

    class Meta:
        verbose_name = "Hisobot formasi"
        verbose_name_plural = "Hisobot formalari"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_used', 'parent']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return getattr(self, "name_uz", self.name)
