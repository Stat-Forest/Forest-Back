from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group

from apps.users.models import CustomUser


def setup_roles_and_permissions():
    user_content_type = ContentType.objects.get_for_model(CustomUser)

    permissions_data = [
        ('can_view_report', 'Can view report'),
        ('can_upload_report', 'Can upload report'),
        ('can_accept_report', 'Can accept report'),
        ('can_return_report', 'Can return report'),
        ('can_add_plan', 'Can add plan'),
        ('can_crud_report', 'Can CRUD report'),
    ]

    for code_name, name in permissions_data:
        Permission.objects.get_or_create(
            code_name=code_name,
            name=name,
            content_type=user_content_type
        )

    groups_permissions = {
        "SuperUser": Permission.objects.all(),
        "Rahbariyat": Permission.objects.filter(codename__in=["can_view_report", "can_upload_report"]),
        "Bo`limAdmin": Permission.objects.filter(codename__in=["can_accept_report", "can_return_report", "can_add_plan"]),
        "TashkilotRahbari": Permission.objects.filter(codename__in=["can_view_report", "can_return_report"]),
        "TashkilotHodimlari": Permission.objects.filter(codename__in=["can_crud_report"])
    }

    for group_name, perms in groups_permissions:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.set(perms)