from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Initializes groups and permissions"

    def handle(self, *args, **kwargs):
        content_type = ContentType.objects.get_for_model(CustomUser)

        permissions = [
            ("can_view_report", "Can view report"),
            ("can_upload_report", "Can upload report"),
            ("can_accept_report", "Can accept report"),
            ("can_return_report", "Can return report"),
            ("can_add_plan", "Can add plan"),
            ("can_crud_report", "Can CRUD report"),
        ]

        for code, name in permissions:
            Permission.objects.get_or_create(
                codename=code, name=name, content_type=content_type
            )

        group_map = {
            "super_admin": Permission.objects.all(),
            "rahbariyat": Permission.objects.filter(codename__in=["can_view_report", "can_upload_report"]),
            "bolim_admin": Permission.objects.filter(codename__in=["can_accept_report", "can_return_report", "can_add_plan"]),
            "tashkilot_rahbari": Permission.objects.filter(codename__in=["can_view_report", "can_return_report"]),
            "tashkilot_hodimi": Permission.objects.filter(codename__in=["can_crud_report"]),
        }

        for group_name, perms in group_map.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            group.permissions.set(perms)

        self.stdout.write(self.style.SUCCESS("Groups and permissions created successfully."))
