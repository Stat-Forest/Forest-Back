from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class HistoryActionJournal(models.Model):
    ACTION_CHOICES = [
        ('add', 'Added'),
        ('change', 'Changed'),
        ('delete', 'Deleted'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=255, blank=True)
    object_id = models.CharField(max_length=255, blank=True, null=True)
    change_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Foydalanuvchi amallari tarixi"
        verbose_name_plural = "Foydalanuvchi amallari tarixi"

    def __str__(self):
        return f"{self.user} {self.action} {self.model_name} ({self.object_repr})"

