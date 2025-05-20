from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.users.models import CustomUser
from faker import Faker

fake = Faker()


def setup_roles_permissions_and_users():
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
            codename=code_name,
            name=name,
            content_type=user_content_type
        )

    groups_permissions = {
        "super_admin": ["can_view_report", "can_upload_report", "can_accept_report", "can_return_report", "can_add_plan", "can_crud_report"],
        "rahbariyat": ["can_view_report", "can_upload_report"],
        "bolim_admin": ["can_accept_report", "can_return_report", "can_add_plan"],
        "tashkilot_rahbari": ["can_view_report", "can_return_report"],
        "tashkilot_hodimi": ["can_crud_report"],
        "hududiy_boshqarma": []
    }

    for group_name, codename_list in groups_permissions.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permissions = Permission.objects.filter(codename__in=codename_list)
        group.permissions.set(permissions)

    for role in CustomUser.Role.values:
        email = f"{role}@test.uz"

        is_staff = role == CustomUser.Role.SUPER_ADMIN
        is_superuser = role == CustomUser.Role.SUPER_ADMIN
        is_active = True

        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "father_name": fake.first_name(),
                "role": role,
                "user_number": f"U{CustomUser.objects.count() + 1:05}",
                "gender": CustomUser.Gender.MALE,
                "nationality": CustomUser.Nation.UZBEK,
                "passport_number": fake.bothify(text="??#######"),
                "date_of_birth": fake.date_of_birth(minimum_age=25, maximum_age=50),
                "date_of_place": fake.city(),
                "address": fake.address(),
                "is_active": is_active,
                "is_staff": is_staff,
                "is_superuser": is_superuser
            }
        )

        if created:
            user.set_password("TestPassword123")
            user.save()
            print(f"Created user: {email}")

        group = Group.objects.filter(name=role).first()
        if group:
            user.groups.set([group])
            print(f"Assigned group '{group.name}' to user '{email}'")
