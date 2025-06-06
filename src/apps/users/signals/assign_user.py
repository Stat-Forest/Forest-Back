from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import Group

from apps.users.models import CustomUser


@receiver(post_save, sender=CustomUser)
def assign_user_to_group(sender, instance, created, **kwargs):
    user_role = instance.role

    role_group_map = {
        CustomUser.Role.SUPER_ADMIN: "super_admin",
        CustomUser.Role.RAHBARIYAT: "rahbariyat",
        CustomUser.Role.BOLIM_ADMIN: "bolim_admin",
        CustomUser.Role.TASHKILOT_RAHBARI: "tashkilot_rahbari",
        CustomUser.Role.TASHKILOT_HODIMI: "tashkilot_hodimi",
        CustomUser.Role.HUDUDIY_BOSHQARMA: "hududiy_boshqarma"
    }

    group_name = role_group_map.get(user_role)

    if group_name:
        try:
            group = Group.objects.get(name=group_name)
            instance.groups.set([group])
        except Group.DoesNotExist:
            print(f"Group name {group_name} not found.")