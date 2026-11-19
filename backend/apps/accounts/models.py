"""Account-domain models: USER, PASSENGER, DRIVER, VEHICLE, LGU_UNIT, ACCREDITATION.

Tables 1-6 in database/schema_listing.md.

USER uses class-table inheritance: PASSENGER and DRIVER share the supertype's
primary key rather than duplicating its columns. Django does not model
inheritance directly, so the subtype declares a OneToOneField that is also its
primary key, with db_column naming the schema's column.
"""

import uuid
from datetime import date

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.enums import AccountStatus, AccredStatus, UserRole

from .managers import UserManager

# Philippine mobile numbers, with or without the +63 country code.
PHONE_VALIDATOR = RegexValidator(
    regex=r"^(\+63|0)9\d{9}$",
    message="Enter a Philippine mobile number, e.g. 09171234567 or +639171234567.",
)


class User(AbstractBaseUser, PermissionsMixin):
    """Supertype for every person on the platform.

    Table 1. ``phone`` is the login identifier (``USERNAME_FIELD``), so it
    carries a UNIQUE constraint — see the design-change note for this step.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="user_id")

    full_name = models.CharField(max_length=120)
    phone = models.CharField(
        max_length=15, unique=True, validators=[PHONE_VALIDATOR]
    )
    email = models.EmailField(max_length=120, null=True, blank=True)
    # db_column keeps the schema's name. Django's own attribute is `password`.
    password = models.CharField(max_length=255, db_column="password_hash")
    registration_date = models.DateField(default=date.today)

    user_role = models.CharField(
        max_length=12, choices=UserRole.choices, default=UserRole.PASSENGER
    )
    account_status = models.CharField(
        max_length=12, choices=AccountStatus.choices, default=AccountStatus.ACTIVE
    )

    # ── Infrastructure columns added for Django's auth framework ──
    # Recorded as a design change; not part of the UML domain model.
    last_login = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]  # prompted by createsuperuser

    class Meta:
        db_table = "USER"
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-registration_date", "full_name"]
        indexes = [
            models.Index(fields=["user_role"], name="idx_user_role"),
            models.Index(fields=["account_status"], name="idx_user_status"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone})"

    # ── Properties ─────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """Django's auth backend checks this before allowing a login.

        Derived from the domain's own ``account_status`` rather than stored
        separately, so the two can never disagree.
        """
        return self.account_status == AccountStatus.ACTIVE

    @property
    def is_passenger(self) -> bool:
        return self.user_role == UserRole.PASSENGER

    @property
    def is_driver(self) -> bool:
        return self.user_role == UserRole.DRIVER

    @property
    def first_name(self) -> str:
        """Used by the admin site's header. Splits on the first space."""
        return self.full_name.split(" ")[0] if self.full_name else ""


class Passenger(models.Model):
    """Subtype of USER. Table 2.

    ``user`` is both the OneToOne link and the primary key, which is how
    class-table inheritance is expressed: PASSENGER.passenger_id is a FK to
    USER.user_id and there is no separate surrogate key.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="passenger_profile",
        db_column="passenger_id",
        limit_choices_to={"user_role": UserRole.PASSENGER},
    )

    home_address = models.CharField(max_length=255)
    gcash_number = models.CharField(max_length=15, validators=[PHONE_VALIDATOR])
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "PASSENGER"
        verbose_name = "passenger"
        verbose_name_plural = "passengers"

    def __str__(self) -> str:
        return f"Passenger: {self.user.full_name}"

    def clean(self):
        """The discriminator and the subtype must agree."""
        from django.core.exceptions import ValidationError

        if self.user_id and self.user.user_role != UserRole.PASSENGER:
            raise ValidationError(
                {"user": "A passenger profile requires user_role=PASSENGER."}
            )

    @property
    def rating_avg(self):
        """Derived — averaged from RATING, never stored.

        schema_listing.md marks this DERIVED. Returning None rather than 0
        for a passenger with no ratings keeps "unrated" distinct from "rated
        zero", which the UI needs.
        """
        from django.db.models import Avg

        from apps.rides.models import Rating

        result = Rating.objects.filter(ratee_user_id=self.user_id).aggregate(
            avg=Avg("stars")
        )["avg"]
        return round(result, 1) if result is not None else None

    @property
    def preferred_mode_names(self):
        """Resolves the multivalued attribute, ordered by preferred_rank.

        Note the name: ``preferred_modes`` is the reverse accessor Django
        creates from PASSENGER_PREFERRED_MODE (Step 05). Naming this property
        the same thing would shadow it and recurse.
        """
        return list(
            self.preferred_modes.order_by("preferred_rank").values_list(
                "mode__mode_name", flat=True
            )
        )


class Driver(models.Model):
    """Subtype of USER. Table 3."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="driver_profile",
        db_column="driver_id",
        limit_choices_to={"user_role": UserRole.DRIVER},
    )

    license_number = models.CharField(max_length=30, unique=True)
    accreditation_status = models.CharField(
        max_length=12, choices=AccredStatus.choices, default=AccredStatus.PENDING
    )
    is_online = models.BooleanField(default=False)
    # Cached aggregates — stored and refreshed, not computed on read.
    # schema_listing.md documents why: both are read on every match.
    rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True
    )
    total_trips = models.IntegerField(default=0)

    class Meta:
        db_table = "DRIVER"
        verbose_name = "driver"
        verbose_name_plural = "drivers"
        indexes = [
            # The matching engine's hot query: online, verified drivers.
            models.Index(fields=["is_online", "accreditation_status"], name="idx_driver_avail"),
        ]

    def __str__(self) -> str:
        return f"Driver: {self.user.full_name} ({self.license_number})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.user_id and self.user.user_role != UserRole.DRIVER:
            raise ValidationError(
                {"user": "A driver profile requires user_role=DRIVER."}
            )

    @property
    def is_available(self) -> bool:
        """Eligible to receive ride requests."""
        return (
            self.is_online
            and self.accreditation_status == AccredStatus.VERIFIED
            and self.user.account_status == AccountStatus.ACTIVE
        )


class LGUUnit(models.Model):
    """A city or municipal LGU that issues driver accreditation. Table 6.

    Promoted from what the class diagram carried as a bare
    ``Accreditation.issuingLGU`` string, so an LGU's name, province and
    contact details have somewhere to live.
    """

    lgu_code = models.CharField(max_length=12, primary_key=True)
    lgu_name = models.CharField(max_length=80)
    province = models.CharField(max_length=60)
    region = models.CharField(max_length=40)
    contact_no = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = "LGU_UNIT"
        verbose_name = "LGU unit"
        verbose_name_plural = "LGU units"
        ordering = ["region", "province", "lgu_name"]

    def __str__(self) -> str:
        return f"{self.lgu_name}, {self.province}"


class Vehicle(models.Model):
    """A driver's registered vehicle. Table 4.

    ``driver_id`` is NOT NULL + UNIQUE: every vehicle has exactly one driver,
    and a driver has at most one vehicle (1 : 0..1 in the schema).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="vehicle_id")
    driver = models.OneToOneField(
        Driver, on_delete=models.CASCADE, related_name="vehicle", db_column="driver_id"
    )
    mode = models.ForeignKey(
        "rides.RideModeLookup",
        on_delete=models.PROTECT,
        related_name="vehicles",
        db_column="mode_code",
        to_field="mode_code",
    )
    plate_number = models.CharField(max_length=12, unique=True)
    model = models.CharField(max_length=60)
    capacity = models.SmallIntegerField(null=True, blank=True)
    route_info = models.CharField(max_length=120, null=True, blank=True)

    class Meta:
        db_table = "VEHICLE"
        verbose_name = "vehicle"
        verbose_name_plural = "vehicles"

    def __str__(self) -> str:
        return f"{self.plate_number} ({self.model})"


class Accreditation(models.Model):
    """Sertipikadong Manong — an LGU-issued driver badge. Table 5.

    A driver has 0..* accreditations: newly registered drivers hold none yet,
    and a driver working across two cities holds two.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="accreditation_id")
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name="accreditations",
        db_column="driver_id",
    )
    lgu = models.ForeignKey(
        LGUUnit,
        on_delete=models.PROTECT,
        related_name="accreditations",
        db_column="lgu_code",
        to_field="lgu_code",
    )
    badge_no = models.CharField(max_length=20, unique=True)
    status = models.CharField(
        max_length=12, choices=AccredStatus.choices, default=AccredStatus.PENDING
    )
    expiry_date = models.DateField()
    badge_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "ACCREDITATION"
        verbose_name = "accreditation"
        verbose_name_plural = "accreditations"
        ordering = ["-expiry_date"]
        constraints = [
            # A driver cannot hold two badges from the same LGU.
            models.UniqueConstraint(
                fields=["driver", "lgu"], name="uq_accreditation_driver_lgu"
            ),
        ]

    def __str__(self) -> str:
        return f"Badge {self.badge_no} ({self.lgu.lgu_name})"

    @property
    def is_expired(self) -> bool:
        return self.expiry_date < timezone.localdate()

    @property
    def is_valid(self) -> bool:
        return self.status == AccredStatus.VERIFIED and not self.is_expired
