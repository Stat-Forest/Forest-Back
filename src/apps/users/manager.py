from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager


class CustomUserManager(UserManager):
    """
    Custom user model manager where email is the unique identifier
    """
    def _create_user(self, email, password, **extra_fields): # type: ignore
        """
        Create and save a User with the given (email) and password.
        :param email: User's email address
        :param password: User's password
        :param extra_fields: Additional fields
        :return: User instance
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email=email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields): # type: ignore
        """
        Creates and saves a new user
        :param email: User's email address.
        :param password: User's password
        :param extra_fields: Additional fields
        :return: User instance
        """
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_staff", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):  # type: ignore
        # extra_fields.setdefault("is_superuser", True)
        # extra_fields.setdefault("is_staff", True)
        # extra_fields.setdefault("is_active", True)
        #
        # if not extra_fields.get("first_name"):
        #     raise ValueError("Superuser must have a first_name.")
        #
        # if extra_fields.get("is_staff") is not True:
        #     raise ValueError("Superuser must have is_staff=True.")
        # if extra_fields.get("is_superuser") is not True:
        #     raise ValueError("Superuser must have is_superuser=True.")
        extra_fields["is_superuser"] = extra_fields["is_staff"] = True
        return self._create_user(email, password, **extra_fields)



