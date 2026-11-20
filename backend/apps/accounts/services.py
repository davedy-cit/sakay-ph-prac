"""Account-domain services — the logic the views are thin wrappers over.

Registration writes two tables atomically (USER + its subtype profile) under a
password policy; the OTP flow is a Redis contract with a TTL. Neither belongs
in a view or a serializer.
"""

import secrets

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import Driver, Passenger, User
from apps.core.enums import UserRole


class RegistrationError(Exception):
    """A field-level registration failure the view turns into a 400."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(message)


class RegistrationService:
    """Creates a USER and its subtype profile in one transaction."""

    @staticmethod
    def register(*, phone: str, password: str, full_name: str, role: str,
                 **profile) -> User:
        if User.objects.filter(phone=phone).exists():
            raise RegistrationError("phone", "That phone number is already registered.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise RegistrationError("password", " ".join(exc.messages))

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    phone=phone, password=password, full_name=full_name, user_role=role,
                )
                if role == UserRole.PASSENGER:
                    Passenger.objects.create(
                        user=user,
                        home_address=profile["home_address"],
                        gcash_number=profile["gcash_number"],
                    )
                elif role == UserRole.DRIVER:
                    Driver.objects.create(user=user, license_number=profile["license_number"])
                else:
                    raise RegistrationError(
                        "role", "Self-registration is for passengers and drivers only."
                    )
        except KeyError as exc:
            # A missing profile field — the serializer should have caught it,
            # but the service owns the rule, so it re-checks.
            raise RegistrationError(exc.args[0], "This field is required.") from exc
        return user


class OtpError(Exception):
    """A non-field OTP failure, e.g. the re-send cooldown."""


class OtpService:
    """Simulated OTP — decision D-14.

    The code lives only in Redis under ``sakayph:otp:<phone>`` with a TTL from
    ``.env`` (``OTP_TTL_SECONDS``), never in MySQL: an OTP is ephemeral by
    definition, and Redis expires it without a cleanup job. A 60-second
    cooldown key stops a burst of re-sends. No SMS gateway is called — the
    code is returned to a DEBUG caller, which is what makes the flow
    demonstrable end to end.
    """

    KEY = "otp:{phone}"
    COOLDOWN_KEY = "otp-cooldown:{phone}"
    COOLDOWN_SECONDS = 60

    @classmethod
    def request_code(cls, phone: str) -> str:
        if cache.get(cls.COOLDOWN_KEY.format(phone=phone)):
            raise OtpError("Another code was sent recently. Wait a minute and retry.")
        code = f"{secrets.randbelow(1_000_000):06d}"
        cache.set(cls.KEY.format(phone=phone), code, settings.OTP_TTL_SECONDS)
        cache.set(cls.COOLDOWN_KEY.format(phone=phone), 1, cls.COOLDOWN_SECONDS)
        return code

    @classmethod
    def verify(cls, phone: str, code: str) -> bool:
        """One attempt per code: a correct code deletes itself on use."""
        key = cls.KEY.format(phone=phone)
        stored = cache.get(key)
        if stored is None or stored != code:
            return False
        cache.delete(key)
        return True
