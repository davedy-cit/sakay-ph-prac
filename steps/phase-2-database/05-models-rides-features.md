# Step 2.05 — Models: Rides Features

| | |
|---|---|
| **Goal** | SURGE_PERIOD, PAKYAWAN_GROUP, PASSENGER_PREFERRED_MODE, TRIP_TRACKING, CANCELLATION and RATING exist — the six tables the seven features hang off |
| **Day / Time** | Day 12 (Tue 17 Nov) · ~3 hours |
| **Prerequisites** | [Step 2.04](04-models-rides-core.md) |
| **Produces** | Six more models in `backend/apps/rides/models.py` |

---

## What each of these is for

Six models, and each one is a feature's storage. If you can say which feature owns
which table, you understand your own design:

| Model | Feature | Notes |
|---|---|---|
| `SurgePeriod` | **Bagyo Mode** | The fare multiplier window. Added by the database design — the concept paper described it but the class diagram had no home for it |
| `PakyawanGroup` | **Pakyawan** | A share-ride group forming on a route |
| `PassengerPreferredMode` | **Lahat ng Sakyan** | Resolves the multivalued `Passenger.preferredModes` |
| `TripTracking` | **Saan ang Jeep?** | Position pings. The only BIGINT-keyed, high-volume table in the schema |
| `Cancellation` | — | The cancel-trip use case, with its fee and refund |
| `Rating` | — | The unary relationship: RATING points at USER twice |

---

## Do this

### 1. Append the six models (~120 min)

Add to `backend/apps/rides/models.py`. Extend the imports:

```python
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.enums import (
    DeliveryStatus,
    GroupStatus,
    RideMode,
    RideStatus,
    SurgeTrigger,
)
```

Then:

```python
class SurgePeriod(models.Model):
    """A window during which a fare multiplier applies. Table 8. Bagyo Mode.

    ``lgu`` is nullable on purpose: a demand surge the platform raises has no
    LGU behind it, while a typhoon declaration or an LGU advisory does. That
    is the 0..1 : 0..* cardinality in schema_listing.md.

    RIDE_LEG.surge records which period a leg was actually priced under, so a
    fare stays explainable after the window closes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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
```

**Four things to notice.**

**`TripTracking` is the only BIGINT key.** Everything else in this project uses a
UUID. That inconsistency is deliberate and the class docstring says why. When an
assessor asks "why is this one different", the answer is in the code.

**The `Rating` unary relationship needs two `related_name`s.** Django raises
`fields.E304: Reverse accessor for 'Rating.rater_user' clashes with reverse accessor
for 'Rating.ratee_user'` without them. This is the single most likely error in this
step.

**`Rating.save()` refreshes `Driver.rating`.** That is the cached aggregate being
maintained. Note it uses `.update()` rather than `.save()` — a targeted UPDATE avoids
a race where two concurrent ratings each write a stale full row.

**`SurgePeriod.active_at()` orders by multiplier descending.** Two overlapping
windows are a real possibility (a national typhoon signal and a city advisory), and
the design has to say which wins. The code says the higher one does.

### 2. Migrate (~15 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
python manage.py makemigrations rides
python manage.py migrate
```

### 3. Prove the constraints and the unary relationship (~45 min)

In `manage.py shell`:

```python
from datetime import timedelta
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Driver, Passenger, User
from apps.core.enums import GroupStatus, RideMode, RideStatus, SurgeTrigger, UserRole
from apps.rides.models import (
    Cancellation, Location, PakyawanGroup, PassengerPreferredMode,
    Rating, Ride, RideLeg, RideModeLookup, SurgePeriod, TripTracking,
)

# ── Fixtures ───────────────────────────────────────────────────
tricycle = RideModeLookup.objects.get(mode_code=RideMode.TRICYCLE)
car = RideModeLookup.objects.get(mode_code=RideMode.CAR) if \
    RideModeLookup.objects.filter(mode_code=RideMode.CAR).exists() else tricycle

pax_user = User.objects.create_user(phone="09170000010", password="t", full_name="Ana Reyes",
                                    user_role=UserRole.PASSENGER)
pax = Passenger.objects.create(user=pax_user, home_address="X", gcash_number="09170000010")
drv_user = User.objects.create_user(phone="09170000011", password="t", full_name="Ben Cruz",
                                    user_role=UserRole.DRIVER)
drv = Driver.objects.create(user=drv_user, license_number="N01-23-456789")

a = Location.objects.create(street="A", barangay="Poblacion", city="Cabuyao",
                            province="Laguna", latitude=Decimal("14.27"), longitude=Decimal("121.12"))
b = Location.objects.create(street="B", barangay="Poblacion", city="Cabuyao",
                            province="Laguna", latitude=Decimal("14.28"), longitude=Decimal("121.13"))

ride = Ride.objects.create(passenger=pax, driver=drv, mode=tricycle,
                           pickup_location=a, dropoff_location=b,
                           status=RideStatus.COMPLETED)
RideLeg.objects.create(ride=ride, leg_no=1, mode=tricycle, driver=drv,
                       origin_location=a, dest_location=b, fare=Decimal("45.00"))
ride.recompute_chain_flags()

# ── 1. Bagyo Mode: only the open window is current ─────────────
now = timezone.now()
past = SurgePeriod.objects.create(surge_label="Bagyo: Signal No. 2",
    trigger_type=SurgeTrigger.WEATHER, multiplier=Decimal("1.50"),
    starts_at=now - timedelta(hours=5), ends_at=now - timedelta(hours=1))
live = SurgePeriod.objects.create(surge_label="Bagyo: Signal No. 1",
    trigger_type=SurgeTrigger.WEATHER, multiplier=Decimal("1.25"),
    starts_at=now - timedelta(minutes=30), ends_at=now + timedelta(hours=2))
print("past current:", past.is_current)                      # False
print("live current:", live.is_current)                      # True
print("active_at now:", SurgePeriod.active_at().surge_label)  # Bagyo: Signal No. 1

# 2. The higher multiplier wins when windows overlap
both = SurgePeriod.objects.create(surge_label="Demand spike",
    trigger_type=SurgeTrigger.DEMAND, multiplier=Decimal("1.80"),
    starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(minutes=30))
print("overlap winner:", SurgePeriod.active_at().surge_label)  # Demand spike

# 3. ends_at must be after starts_at
try:
    with transaction.atomic():
        SurgePeriod.objects.create(surge_label="Bad", trigger_type=SurgeTrigger.MANUAL,
            multiplier=Decimal("2.00"), starts_at=now, ends_at=now - timedelta(hours=1))
    print("*** BAD WINDOW ALLOWED ***")
except IntegrityError:
    print("inverted window rejected: True")

# 4. A multiplier below 1.0 is rejected
try:
    with transaction.atomic():
        SurgePeriod.objects.create(surge_label="Discount", trigger_type=SurgeTrigger.MANUAL,
            multiplier=Decimal("0.50"), starts_at=now, ends_at=now + timedelta(hours=1))
    print("*** SURCHARGE BELOW 1.0 ALLOWED ***")
except IntegrityError:
    print("multiplier < 1 rejected: True")

# ── 5. Pakyawan capacity ───────────────────────────────────────
grp = PakyawanGroup.objects.create(ride=ride, direction="Cabuyao → Sta. Rosa",
                                   max_seats=4)
print("seats:", grp.seats_available)                         # 4
for _ in range(4):
    grp.add_seat()
print("after 4 seats:", grp.matched_seats, grp.group_status, "| full:", grp.is_full)
print("5th seat accepted:", grp.add_seat())                  # False
try:
    with transaction.atomic():
        PakyawanGroup.objects.filter(pk=grp.pk).update(matched_seats=99)
    print("*** OVERCAPACITY ALLOWED ***")
except IntegrityError:
    print("overcapacity rejected: True")

# ── 6. Preferred modes: multivalued attribute + rank ───────────
PassengerPreferredMode.objects.create(passenger=pax, mode=tricycle, preferred_rank=1)
PassengerPreferredMode.objects.create(passenger=pax, mode=car, preferred_rank=2)
print("preferred:", pax.preferred_mode_names)
try:
    with transaction.atomic():
        PassengerPreferredMode.objects.create(passenger=pax, mode=tricycle, preferred_rank=9)
    print("*** DUPLICATE PREFERRED MODE ALLOWED ***")
except IntegrityError:
    print("duplicate (passenger, mode) rejected: True")

# ── 7. Trip tracking: latest and trail ─────────────────────────
for i in range(3):
    TripTracking.objects.create(ride=ride, latitude=Decimal("14.27") + Decimal(i) / 1000,
                                longitude=Decimal("121.12"),
                                recorded_at=now + timedelta(seconds=i * 10))
print("pings:", TripTracking.objects.filter(ride=ride).count())        # 3
print("latest:", TripTracking.latest_for(ride).recorded_at == now + timedelta(seconds=20))
print("trail oldest-first:", [p.recorded_at.second for p in TripTracking.trail_for(ride)])

# ── 8. Rating: the unary relationship and the cached aggregate ─
Rating.objects.create(ride=ride, rater_user=pax_user, ratee_user=drv_user,
                      stars=5, comment="Maayos ang biyahe.")
drv.refresh_from_db()
print("driver rating cached:", drv.rating)                   # 5.0

try:
    with transaction.atomic():
        Rating.objects.create(ride=ride, rater_user=pax_user, ratee_user=drv_user, stars=1)
    print("*** DOUBLE RATING ALLOWED ***")
except IntegrityError:
    print("second rating by same rater rejected: True")

try:
    with transaction.atomic():
        Rating.objects.create(ride=ride, rater_user=drv_user, ratee_user=drv_user, stars=5)
    print("*** SELF-RATING ALLOWED ***")
except IntegrityError:
    print("self-rating rejected: True")

try:
    with transaction.atomic():
        Rating.objects.create(ride=ride, rater_user=drv_user, ratee_user=pax_user, stars=9)
    print("*** 9 STARS ALLOWED ***")
except IntegrityError:
    print("stars > 5 rejected: True")

# ── 9. Passenger.rating_avg is derived, not stored ─────────────
print("passenger rating_avg:", pax.rating_avg)               # None (not rated)
print("is a column?", "rating_avg" in [f.name for f in Passenger._meta.get_fields()])

# ── Clean up ───────────────────────────────────────────────────
Ride.objects.filter(pk=ride.pk).delete()
User.objects.filter(pk__in=[pax_user.pk, drv_user.pk]).delete()
SurgePeriod.objects.filter(pk__in=[past.pk, live.pk, both.pk]).delete()
Location.objects.filter(pk__in=[a.pk, b.pk]).delete()
exit()
```

Expected: **every `*** ... ***` line absent**, and every "rejected: True" present.
Those starred lines are the failures — if one prints, that constraint is not in the
database.

### 4. Confirm in MySQL (~15 min)

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW TABLES;"
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW CREATE TABLE RATING\G"
```

In `RATING` you should see two foreign keys both pointing at `USER`, with different
constraint names. That is the unary relationship in the DDL.

### 5. Commit (~10 min)

```powershell
Set-Location ..
git add backend/apps/rides/
git commit -m "feat(rides): add surge, Pakyawan, preferred modes, tracking, cancellation, rating"
git push
```

---

## Verify

- [ ] All six models migrated without error
- [ ] `SHOW CREATE TABLE RATING` shows two FKs to `USER`
- [ ] `SurgePeriod.active_at()` returns the highest multiplier among overlapping windows
- [ ] An inverted surge window raises `IntegrityError`
- [ ] `multiplier < 1` raises `IntegrityError`
- [ ] `PakyawanGroup.add_seat()` refuses past `max_seats`, and the constraint backs it up
- [ ] A duplicate `(passenger, mode)` raises `IntegrityError`
- [ ] `TripTracking.latest_for()` and `.trail_for()` return the right rows
- [ ] `Driver.rating` updates when a rating is saved
- [ ] Self-rating, double-rating and `stars=9` all raise `IntegrityError`
- [ ] `Passenger.rating_avg` is a property, not a field
- [ ] Every `*** ... ***` failure line was absent
- [ ] Committed and pushed

---

## Log it

```markdown
**Step 2.05 — rides feature models — DONE**

- Added SURGE_PERIOD (nullable LGU, active_at() picks highest multiplier),
  PAKYAWAN_GROUP (capacity constraints), PASSENGER_PREFERRED_MODE,
  TRIP_TRACKING (BigAutoField — only non-UUID key, high-volume time series),
  CANCELLATION, RATING (unary relationship, two related_names)
- Rating.save() refreshes the cached DRIVER.rating aggregate via .update()
- Added CHECK constraints: surge window order, multiplier >= 1, seat capacity,
  stars 1..5, no self-rating; UNIQUE (ride, rater_user)
- Verified 9 behavioural checks in shell — all constraints enforced
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `fields.E304: Reverse accessor ... clashes` | The two `Rating` FKs share a default `related_name` | Set `related_name="ratings_written"` and `"ratings_received"` |
| `fields.E302` / `E303` | Same problem on `RideLeg.origin_location` / `dest_location` | They already have distinct names — check you copied them |
| `Cannot resolve keyword 'surge'` | `SurgePeriod` is defined after `RideLeg` | Django resolves string references lazily, so order does not matter — check the spelling `"rides.SurgePeriod"` |
| `CheckConstraint` import error | Django 6 removed `check=` | Use `condition=` |
| Overcapacity write succeeded | MySQL older than 8.0.16 ignores CHECK | You are on 8.4. If it still passes, the constraint is missing from the migration |
| `Driver.rating` stays `None` | `_refresh_driver_rating` found no Driver for that user | It looks up `Driver.objects.filter(user_id=...)` — confirm the ratee is a driver |
| `TripTracking` migration uses `char(32)` | You gave it a UUID PK | It must be `BigAutoField` — see the schema, table 23 |
| `pax.preferred_mode_names` returns `[]` | `related_name` mismatch | `PassengerPreferredMode.passenger` must have `related_name="preferred_modes"` |

---

## After this step

Every ride-domain table exists. What is left is money — payments, wallets, fare
splits, receipts and the driver payout ledger.

Next: [06 — Models: payments](06-models-payments.md)
