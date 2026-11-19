"""Ride-domain models.

Written incrementally across Steps 03-05. This step contributes only
RIDE_MODE, because Vehicle in the accounts app references it.
"""

from django.db import models

from apps.core.enums import RideMode

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from apps.core.enums import RideMode, RideStatus


from apps.core.enums import (
    DeliveryStatus,
    GroupStatus,
    RideMode,
    RideStatus,
    SurgeTrigger,
)

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

    """ Bagyo Mode: records the multiplier actually applied to this leg, so a
    # fare can be explained after the surge window has closed.
    # UNCOMMENT IN STEP 05 — `SurgePeriod` is written there, and makemigrations
    cannot resolve "rides.SurgePeriod" until it exists:
    """
    surge = models.ForeignKey(
        "rides.SurgePeriod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legs",
        db_column="surge_id",
    )

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

# """Step 2.05: models-rides-feature"""
class SurgePeriod(models.Model):
    """A window during which a fare multiplier applies. Table 8. Bagyo Mode.

    ``lgu`` is nullable on purpose: a demand surge the platform raises has no
    LGU behind it, while a typhoon declaration or an LGU advisory does. That
    is the 0..1 : 0..* cardinality in schema_listing.md.

    RIDE_LEG.surge records which period a leg was actually priced under, so a
    fare stays explainable after the window closes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="surge_id")

    lgu = models.ForeignKey(
        "accounts.LGUUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="surge_periods",
        db_column="lgu_code",
        to_field="lgu_code",
    )
    surge_label = models.CharField(
        max_length=40, help_text="Shown to the passenger, e.g. 'Bagyo: Signal No. 2'."
    )
    trigger_type = models.CharField(max_length=12, choices=SurgeTrigger.choices)
    multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(1)],
        help_text="1.50 = a 50% increase.",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "SURGE_PERIOD"
        verbose_name = "surge period"
        verbose_name_plural = "surge periods"
        ordering = ["-starts_at"]
        indexes = [
            # The fare calculator's lookup: active windows covering now.
            models.Index(fields=["is_active", "starts_at", "ends_at"], name="idx_surge_window"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="ck_surge_ends_after_starts",
            ),
            models.CheckConstraint(
                condition=models.Q(multiplier__gte=1), name="ck_surge_multiplier_min_1"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.surge_label} (×{self.multiplier})"

    @property
    def is_current(self) -> bool:
        """True only inside the window and only while still active.

        Both conditions matter: a period can be administratively ended early
        (``is_active=False``) while its window is still open.
        """
        now = timezone.now()
        return self.is_active and self.starts_at <= now <= self.ends_at

    @classmethod
    def active_at(cls, moment=None, lgu=None):
        """The surge in force at ``moment``, or None.

        Ordered by multiplier descending so that if two windows overlap — a
        national typhoon signal and a city advisory, say — the higher one
        wins rather than an arbitrary row.
        """
        moment = moment or timezone.now()
        qs = cls.objects.filter(
            is_active=True, starts_at__lte=moment, ends_at__gte=moment
        )
        if lgu is not None:
            qs = qs.filter(models.Q(lgu=lgu) | models.Q(lgu__isnull=True))
        return qs.order_by("-multiplier").first()


class PakyawanGroup(models.Model):
    """A share-ride group. Table 13.

    One per ride — ``ride`` is NOT NULL + UNIQUE, which is the 1 : 0..1 in
    the schema. A solo ride simply has no group.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="group_id")

    ride = models.OneToOneField(
        Ride, on_delete=models.CASCADE, related_name="pakyawan_group", db_column="ride_id"
    )
    direction = models.CharField(
        max_length=120, help_text="Human-readable route, e.g. 'Cabuyao → Sta. Rosa'."
    )
    max_seats = models.SmallIntegerField(validators=[MinValueValidator(2)])
    matched_seats = models.SmallIntegerField(default=0)
    group_status = models.CharField(
        max_length=12, choices=GroupStatus.choices, default=GroupStatus.FORMING
    )

    class Meta:
        db_table = "PAKYAWAN_GROUP"
        verbose_name = "Pakyawan group"
        verbose_name_plural = "Pakyawan groups"
        indexes = [
            models.Index(fields=["group_status"], name="idx_pakyawan_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(matched_seats__gte=0), name="ck_pakyawan_seats_nonneg"
            ),
            models.CheckConstraint(
                condition=models.Q(matched_seats__lte=models.F("max_seats")),
                name="ck_pakyawan_seats_within_capacity",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.direction} ({self.matched_seats}/{self.max_seats})"

    @property
    def seats_available(self) -> int:
        return max(self.max_seats - self.matched_seats, 0)

    @property
    def is_full(self) -> bool:
        return self.matched_seats >= self.max_seats

    def add_seat(self, save: bool = True) -> bool:
        """Take one seat. Returns False if the group is already full.

        The capacity check is duplicated here and in the CheckConstraint on
        purpose: the constraint is the guarantee, this is the friendly path
        that avoids an IntegrityError in normal operation.
        """
        if self.is_full:
            return False
        self.matched_seats += 1
        if self.is_full:
            self.group_status = GroupStatus.FULL
        if save:
            super().save(update_fields=["matched_seats", "group_status"])
        return True


class PassengerPreferredMode(models.Model):
    """Associative entity: PASSENGER × RIDE_MODE. Table 26.

    Resolves ``Passenger.preferredModes : List<RideMode>``. The documented key
    is ``(passenger_id, mode_code)``; as with RIDE_LEG, uniqueness is enforced
    by a UniqueConstraint because Django has no composite primary key.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    passenger = models.ForeignKey(
        "accounts.Passenger",
        on_delete=models.CASCADE,
        related_name="preferred_modes",
        db_column="passenger_id",
    )
    mode = models.ForeignKey(
        RideModeLookup,
        on_delete=models.CASCADE,
        related_name="preferred_by",
        db_column="mode_code",
    )
    preferred_rank = models.SmallIntegerField(default=1)

    class Meta:
        db_table = "PASSENGER_PREFERRED_MODE"
        verbose_name = "preferred mode"
        verbose_name_plural = "preferred modes"
        ordering = ["passenger", "preferred_rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["passenger", "mode"], name="uq_prefmode_passenger_mode"
            ),
            models.CheckConstraint(
                condition=models.Q(preferred_rank__gte=1),
                name="ck_prefmode_rank_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.passenger.user.full_name} → {self.mode.mode_name} (#{self.preferred_rank})"


class TripTracking(models.Model):
    """A position ping. Table 23. Saan ang Jeep?

    The only BIGINT-keyed table in the schema, and deliberately so: this is
    a high-volume append-only time series. A UUID primary key would be 32
    bytes per row against 8, and the index is written far more often than it
    is read.

    Nothing in Phase 2 writes here. The ``simulate_driver`` management
    command in Phase 3 does — without it the live-tracking demo has no
    movement to show.
    """

    track_id = models.BigAutoField(primary_key=True)

    ride = models.ForeignKey(
        Ride, on_delete=models.CASCADE, related_name="tracking_pings", db_column="ride_id"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "TRIP_TRACKING"
        verbose_name = "trip tracking ping"
        verbose_name_plural = "trip tracking pings"
        ordering = ["ride", "recorded_at"]
        indexes = [
            # "the latest position of this ride" — the only query that matters.
            models.Index(fields=["ride", "-recorded_at"], name="idx_tracking_latest"),
        ]

    def __str__(self) -> str:
        return f"{self.ride_id} @ {self.recorded_at:%H:%M:%S}"

    @classmethod
    def latest_for(cls, ride):
        """The most recent ping for a ride, or None."""
        return cls.objects.filter(ride=ride).order_by("-recorded_at").first()

    @classmethod
    def trail_for(cls, ride, limit: int = 50):
        """The most recent pings, oldest first — the shape Leaflet wants."""
        pings = list(cls.objects.filter(ride=ride).order_by("-recorded_at")[:limit])
        return list(reversed(pings))


class Cancellation(models.Model):
    """A cancelled ride, with its fee and refund. Table 24.

    A row here is a financial record. That is why ``fee_amount`` and
    ``refund_amount`` are stored rather than recomputed from a policy that
    may since have changed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="cancel_id")

    ride = models.OneToOneField(
        Ride, on_delete=models.CASCADE, related_name="cancellation", db_column="ride_id"
    )
    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="cancellations_made",
        db_column="cancelled_by",
    )
    reason_code = models.CharField(max_length=20)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cancelled_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "CANCELLATION"
        verbose_name = "cancellation"
        verbose_name_plural = "cancellations"
        ordering = ["-cancelled_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fee_amount__gte=0), name="ck_cancel_fee_nonneg"
            ),
            models.CheckConstraint(
                condition=models.Q(refund_amount__gte=0), name="ck_cancel_refund_nonneg"
            ),
        ]

    def __str__(self) -> str:
        return f"Cancelled {str(self.ride_id)[:8]} ({self.reason_code})"


class Rating(models.Model):
    """A rating one user gives another about a ride. Table 25.

    **Unary relationship.** ``rater_user`` and ``ratee_user`` both point at
    USER, so both FKs need an explicit ``related_name`` — without one, Django
    cannot tell the two reverse accessors apart and raises
    ``fields.E304``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="rating_id")

    ride = models.ForeignKey(
        Ride, on_delete=models.CASCADE, related_name="ratings", db_column="ride_id"
    )
    rater_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="ratings_written",
        db_column="rater_user_id",
    )
    ratee_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="ratings_received",
        db_column="ratee_user_id",
    )
    stars = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.CharField(max_length=255, blank=True)
    rated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "RATING"
        verbose_name = "rating"
        verbose_name_plural = "ratings"
        ordering = ["-rated_at"]
        indexes = [
            # Driver.rating and Passenger.rating_avg both aggregate over this.
            models.Index(fields=["ratee_user", "-rated_at"], name="idx_rating_ratee"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(stars__gte=1, stars__lte=5),
                name="ck_rating_stars_1_to_5",
            ),
            # Nobody rates themselves.
            models.CheckConstraint(
                condition=~models.Q(rater_user=models.F("ratee_user")),
                name="ck_rating_not_self",
            ),
            # One rating per person per ride.
            models.UniqueConstraint(
                fields=["ride", "rater_user"], name="uq_rating_ride_rater"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.stars}★ for {self.ratee_user.full_name}"

    def save(self, *args, **kwargs):
        """Refresh the ratee's cached aggregate after saving.

        DRIVER.rating is a documented cached aggregate — read on every match,
        so it is stored rather than recomputed. PASSENGER.rating_avg is
        derived and needs no refresh.
        """
        super().save(*args, **kwargs)
        self._refresh_driver_rating()

    def _refresh_driver_rating(self) -> None:
        from django.db.models import Avg

        from apps.accounts.models import Driver

        driver = Driver.objects.filter(user_id=self.ratee_user_id).first()
        if driver is None:
            return
        avg = Rating.objects.filter(ratee_user_id=self.ratee_user_id).aggregate(
            a=Avg("stars")
        )["a"]
        Driver.objects.filter(pk=driver.pk).update(
            rating=round(avg, 1) if avg is not None else None
        )    