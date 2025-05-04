import random

from django.apps import apps


def new_id():
    """
    Generate a new unique ID for a User.

    This function generates a random 8-digit integer and checks if it already
    exists as a user in the User model. If the generated ID
    already exists, the function recursively calls itself to generate a new ID
    until a unique one is found.

    Returns:
        str: A unique 8-digit ID as a string.
    """
    CustomUser = apps.get_model("users", "CustomUser")
    pk = random.randint(100000, 999999)
    if CustomUser.objects.filter(user_number=pk).exists():
        return new_id()
    return str(pk)
