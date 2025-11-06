from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import HistoryActionJournal


def _create_log(user, action, model_name, instance=None, message=None):
    """Helper function to create history logs."""
    if model_name == 'HistoryActionJournal':
        return  # avoid self-logging

    HistoryActionJournal.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_repr=str(instance) if instance else model_name,
        object_id=str(getattr(instance, 'pk', None)) if instance else None,
        change_message=message,
    )


@receiver(post_save)
def log_create_or_update(sender, instance, created, **kwargs):
    """Log create and update actions for all models."""
    user = getattr(instance, '_history_user', None)
    action = 'add' if created else 'change'
    message = f"{sender.__name__} {'created' if created else 'updated'}."
    _create_log(user, action, sender.__name__, instance, message)


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    """Log delete actions for all models."""
    user = getattr(instance, '_history_user', None)
    message = f"{sender.__name__} deleted."
    _create_log(user, 'delete', sender.__name__, instance, message)


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login."""
    _create_log(user, 'login', 'User', message='User logged in.')


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout."""
    _create_log(user, 'logout', 'User', message='User logged out.')
