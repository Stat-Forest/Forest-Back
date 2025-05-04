from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import CustomUser
from apps.users.validations.new_id import new_id


@receiver(post_save, sender=CustomUser)
def set_user_number(sender, instance, created, **kwargs):
    if created and not instance.user_number:
        instance.user_number = new_id()
        instance.save()
