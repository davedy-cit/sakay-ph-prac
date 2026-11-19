"""Managers for the Sakay.ph account models.

The user manager exists because ``User`` uses ``phone`` as its login
identifier rather than ``username``, so Django's default
``UserManager.create_user`` signature does not apply.
"""

from django.contrib.auth.base_user import BaseUserManager

from apps.core.enums import AccountStatus, UserRole


class UserManager(BaseUserManager):
    """Manager for the USER supertype."""

    use_in_migrations = True

    def create_user(self, phone: str, password: str | None = None, **extra):
        """Create and save a user with the given phone number."""
        if not phone:
            raise ValueError("A phone number is required.")
        extra.setdefault("user_role", UserRole.PASSENGER)
        extra.setdefault("account_status", AccountStatus.ACTIVE)

        user = self.model(phone=phone.strip(), **extra)
        # set_password hashes; assigning `password` directly would store
        # plaintext and the login would silently never succeed.
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str, **extra):
        """Create a superuser for the Django admin site."""
        extra.setdefault("user_role", UserRole.ADMIN)
        extra.setdefault("account_status", AccountStatus.ACTIVE)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("full_name", "Administrator")

        if extra.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")

        return self.create_user(phone, password, **extra)
