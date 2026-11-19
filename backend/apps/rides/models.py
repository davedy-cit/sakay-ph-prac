"""Ride-domain models.

Written incrementally across Steps 03-05. This step contributes only
RIDE_MODE, because Vehicle in the accounts app references it.
"""

from django.db import models

from apps.core.enums import RideMode

import uuid
from django.core.validators import MinValueValidator
from django.utils import timezone
from apps.core.enums import RideMode, RideStatus

class RideModeLookup(models.Model):
    """The Lahat ng Sakayan mode list. Table 7.

    Named ``RideModeLookup`` rather than ``RideMode`` because
    ``apps.core.enums.RideMode`` already owns that name — and the enum is
    what every other model uses for its choices.
    """

    mode_code = models.CharField(
        max_length=12, primary_key=True, choices=RideMode.choices
    )
    mode_name = models.CharField(max_length=30)
    base_fare = models.DecimalField(max_digits=8, decimal_places=2)
    per_km_rate = models.DecimalField(max_digits=8, decimal_places=2)
    seat_capacity = models.SmallIntegerField()
    is_shared = models.BooleanField(
        default=False, help_text="Pakyawan-capable mode."
    )
    # ── D-62 (A-13) ────────────────────────────────────────────
    # Required. The mockups show a flat ₱3.00 booking fee on top of the metered
    # fare, and RIDE_MODE is where a per-mode flat fee belongs — one row changes
    # the price for every ride of that mode, with no code deploy.
    booking_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = "RIDE_MODE"
        verbose_name = "ride mode"
        verbose_name_plural = "ride modes"
        ordering = ["base_fare"]

    def __str__(self) -> str:
        return f"{self.mode_name} (₱{self.base_fare} + ₱{self.per_km_rate}/km)"

class Location(models.Model):
    """A pickup or drop-off point. Table 10.

    ``Location.address`` in the class diagram is a composite attribute; it is
    split into street / barangay / city / province here, which is what makes
    "rides from Barangay Poblacion" a query rather than a string match.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="location_id")

    street = models.CharField(max_length=120)
    barangay = models.CharField(max_length=60)
    city = models.CharField(max_length=60)
    province = models.CharField(max_length=60)
    landmark = models.CharField(max_length=120, blank=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        db_table = "LOCATION"
        verbose_name = "location"
        verbose_name_plural = "locations"
        indexes = [
            models.Index(fields=["city", "barangay"], name="idx_location_area"),
            # The matching engine searches by bounding box before distance.
            models.Index(fields=["latitude", "longitude"], name="idx_location_geo"),
        ]

    def __str__(self) -> str:
        parts = [self.street, self.barangay, self.city]
        return ", ".join(p for p in parts if p)

    @property
    def full_address(self) -> str:
        """Reassembles the composite attribute, with the landmark if set."""
        parts = [self.street, self.barangay, self.city, self.province]
        address = ", ".join(p for p in parts if p)
        return f"{address} (near {self.landmark})" if self.landmark else address


class Ride(models.Model):
    """A booking. Table 11.

    A ride is either a single journey or a trip chain of 1..* legs. The
    ``mode``, ``pickup_location`` and ``dropoff_location`` columns are
    documented denormalizations: they repeat the first (or last) leg's values
    so the ride list renders from one row instead of walking the chain.
    schema_listing.md records why each is kept.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="ride_id")

    passenger = models.ForeignKey(
        "accounts.Passenger",
        on_delete=models.PROTECT,
        related_name="rides",
        db_column="passenger_id",
    )
    # NULL until a driver accepts — the 0..1 side of DRIVER -> RIDE.
    driver = models.ForeignKey(
        "accounts.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rides",
        db_column="driver_id",
    )
    vehicle = models.ForeignKey(
        "accounts.Vehicle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rides",
        db_column="vehicle_id",
    )

    # ── Denormalized summary of the chain's first (and last) leg ──
    mode = models.ForeignKey(
        RideModeLookup,
        on_delete=models.PROTECT,
        related_name="rides",
        db_column="mode_code",
    )
    pickup_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="pickups",
        db_column="pickup_location_id",
    )
    dropoff_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="dropoffs",
        db_column="dropoff_location_id",
    )

    status = models.CharField(
        max_length=16, choices=RideStatus.choices, default=RideStatus.REQUESTED
    )
    is_trip_chain = models.BooleanField(default=False)
    leg_count = models.SmallIntegerField(null=True, blank=True)

    fare_estimate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # ── Business timestamps (not audit timestamps) ─────────────
    request_time = models.DateTimeField(default=timezone.now)
    matched_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "RIDE"
        verbose_name = "ride"
        verbose_name_plural = "rides"
        ordering = ["-request_time"]
        indexes = [
            # "my rides" and "my trips", the two list queries.
            models.Index(fields=["passenger", "status"], name="idx_ride_pax_status"),
            models.Index(fields=["driver", "status"], name="idx_ride_drv_status"),
            models.Index(fields=["-request_time"], name="idx_ride_recent"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ended_at__isnull=True)
                | models.Q(ended_at__gte=models.F("request_time")),
                name="ck_ride_ended_after_request",
            ),
        ]

    def __str__(self) -> str:
        return f"Ride {str(self.id)[:8]} — {self.passenger.user.full_name} ({self.status})"

    # ── Derived and denormalized maintenance ───────────────────

    @property
    def final_fare(self):
        """DERIVED — the sum of the legs' fares. Never stored.

        schema_listing.md marks this DERIVED, and it is the right call: a
        stored total would be a second source of truth that drifts the first
        time a leg is re-priced.
        """
        total = self.legs.aggregate(total=models.Sum("fare"))["total"]
        return total

    def recompute_leg_count(self, save: bool = True) -> int:
        """Refresh the denormalized ``leg_count`` from the actual legs."""
        count = self.legs.count()
        if save and count != self.leg_count:
            self.leg_count = count
            super().save(update_fields=["leg_count"])
        else:
            self.leg_count = count
        return count

    def recompute_chain_flags(self, save: bool = True) -> None:
        """Refresh ``leg_count`` and ``is_trip_chain`` together.

        Call this after adding or removing legs. Both columns summarize the
        chain, so they are recomputed from the same query rather than
        maintained by hand at each call site.
        """
        count = self.recompute_leg_count(save=False)
        self.is_trip_chain = count > 1
        if save:
            super().save(update_fields=["leg_count", "is_trip_chain"])

    @property
    def duration_minutes(self):
        """Wall-clock duration, or None while the ride is still running."""
        if not self.ended_at:
            return None
        return round((self.ended_at - self.request_time).total_seconds() / 60)


class RideLeg(models.Model):
    """One segment of a ride. Table 12. Weak entity.

    Identified by ``(ride_id, leg_no)`` — a leg has no identity apart from its
    parent ride. Django cannot declare a composite primary key, so uniqueness
    is enforced with a UniqueConstraint; see the design note at the top of
    this step.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,  # identifying relationship
        related_name="legs",
        db_column="ride_id",
    )
    leg_no = models.SmallIntegerField(validators=[MinValueValidator(1)])

    mode = models.ForeignKey(
        RideModeLookup,
        on_delete=models.PROTECT,
        related_name="legs",
        db_column="mode_code",
    )
    # Each leg can have a different driver — that is what makes Isang Biyahe
    # a chain rather than one long trip.
    driver = models.ForeignKey(
        "accounts.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legs",
        db_column="driver_id",
    )

    origin_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="legs_as_origin",
        db_column="origin_location_id",
    )
    dest_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="legs_as_destination",
        db_column="dest_location_id",
    )

    fare = models.DecimalField(max_digits=10, decimal_places=2)
    distance_km = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    eta_minutes = models.SmallIntegerField(null=True, blank=True)

    # Bagyo Mode: records the multiplier actually applied to this leg, so a
    # fare can be explained after the surge window has closed.
    # UNCOMMENT IN STEP 05 — `SurgePeriod` is written there, and makemigrations
    # cannot resolve "rides.SurgePeriod" until it exists:
    # surge = models.ForeignKey(
    #     "rides.SurgePeriod",
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name="legs",
    #     db_column="surge_id",
    # )

    status = models.CharField(
        max_length=16, choices=RideStatus.choices, default=RideStatus.REQUESTED
    )

    class Meta:
        db_table = "RIDE_LEG"
        verbose_name = "ride leg"
        verbose_name_plural = "ride legs"
        ordering = ["ride", "leg_no"]
        constraints = [
            # The composite key, as close as Django can express it.
            models.UniqueConstraint(
                fields=["ride", "leg_no"], name="uq_rideleg_ride_legno"
            ),
            models.CheckConstraint(
                condition=models.Q(leg_no__gte=1), name="ck_rideleg_legno_positive"
            ),
            models.CheckConstraint(
                condition=~models.Q(origin_location=models.F("dest_location")),
                name="ck_rideleg_origin_differs_from_dest",
            ),
        ]

    def __str__(self) -> str:
        return f"Leg {self.leg_no} of {str(self.ride_id)[:8]} — {self.mode.mode_name}"

    @property
    def is_first(self) -> bool:
        return self.leg_no == 1

    @property
    def is_last(self) -> bool:
        return self.leg_no == self.ride.leg_count