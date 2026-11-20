"""DRF permission classes — strategy objects the views compose in."""

from rest_framework.permissions import BasePermission


class IsDriver(BasePermission):
    """Allows access only to authenticated users holding a DRIVER role."""

    message = "Only drivers may do this."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_driver
        )