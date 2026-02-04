from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from apps.reports.models import Report
from apps.users.models import CustomUser


def clear_dashboard_cache_for_users(users):
    for user in users:
        cache.delete(f"dashboard:stats:user:{user.id}")


@receiver(post_save, sender=Report)
@receiver(post_delete, sender=Report)
def invalidate_dashboard_cache(sender, instance, **kwargs):
    users = set()

    # ORGANIZATION USERS
    if instance.organization:
        users.update(
            CustomUser.objects.filter(
                organization=instance.organization
            )
        )

        # HUDUDIY BOSHQARMA users
        users.update(
            CustomUser.objects.filter(
                role=CustomUser.Role.HUDUDIY_BOSHQARMA,
                region_user_orgs=instance.organization
            )
        )

    # STATEMENT USERS
    if instance.statement:
        users.update(
            CustomUser.objects.filter(
                statement=instance.statement
            )
        )

    # SUPER / MARKAZIY USERS
    users.update(
        CustomUser.objects.filter(
            organization__isnull=True,
            statement__isnull=True
        )
    )

    clear_dashboard_cache_for_users(users)
