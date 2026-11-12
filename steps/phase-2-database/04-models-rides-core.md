# Step 2.04 — Models: Rides Core

| | |
|---|---|
| **Goal** | LOCATION, RIDE and RIDE_LEG exist; the weak entity's composite key is enforced by the database; a trip chain of legs can be written and read back in order |
| **Day / Time** | Day 11 (Mon 16 Nov) · ~3 hours |
| **Prerequisites** | [Step 2.03](03-models-accounts.md) |
| **Produces** | `Location`, `Ride`, `RideLeg` in `backend/apps/rides/models.py` |

---

## The interesting problem in this step

`RIDE_LEG` is a **weak entity**. It has no identifier of its own — a leg is
identified by `(ride_id, leg_no)`, because "leg 2" means nothing without knowing
which ride it belongs to. That composite key is the single most important
structural idea in your schema, and it is also the one Django cannot express.

**Django has no composite primary keys.** Every model gets one `pk` field. There is
no supported way to declare `PRIMARY KEY (ride_id, leg_no)` through the ORM.

The options, and why this plan picks the third:

| Option | Cost | Verdict |
|---|---|---|
| Third-party package (`django-composite-pk`) | An unmaintained dependency, unfamiliar to an assessor | Rejected |
| Raw SQL in a migration to alter the PK | Hand-written DDL that the ORM does not know about; the next `makemigrations` fights it | Rejected |
| **Surrogate `id` + `UniqueConstraint(ride, leg_no)`** | The PK is not literally composite; the uniqueness guarantee is | **Chosen** |

**What you actually get.** The database enforces that no two legs share
`(ride_id, leg_no)`. It also enforces that `ride_id` is a NOT NULL foreign key,
which is the other half of what makes a weak entity weak — a leg cannot exist
without its ride. What you do not get is a literal two-column primary key in
`SHOW CREATE TABLE`.

**Say this out loud in your report.** A deviation that is explained reads as
engineering judgment. The same deviation left unexplained reads as an oversight.
Record it in `consistency_report.md`:

> **D-67 — Composite primary keys.** Django's ORM does not support composite primary
> keys. The documented key `(ride_id, leg_no)` is implemented as a surrogate `id`
> primary key plus `UNIQUE (ride_id, leg_no)`. Uniqueness and the identifying
> relationship to RIDE are both enforced by the database; only the literal key shape
> differs. The same substitution applies to FARE_SHARE, SOS_NOTIFICATION and
> PASSENGER_PREFERRED_MODE.

**One entry, not four.** This is a single decision applied to four tables, and
splitting it across four numbers would make it read as four unrelated deviations.
Numbering continues from Step 03, which took D-64/65/66 — so this is **D-67**.
Verify the next free number in your own report before you write it.

---

## Do this

### 1. Append LOCATION, RIDE and RIDE_LEG (~90 min)

Add to `backend/apps/rides/models.py`, below `RideModeLookup`. Replace the import
block at the top of the file with:

```python
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.enums import RideMode, RideStatus
```

Then:

```python
class Location(models.Model):
    """A pickup or drop-off point. Table 10.

    ``Location.address`` in the class diagram is a composite attribute; it is
    split into street / barangay / city / province here, which is what makes
    "rides from Barangay Poblacion" a query rather than a string match.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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
```

**Five decisions in there are worth understanding, because an assessor may ask.**

**`on_delete=models.CASCADE` on `RideLeg.ride`.** This is what "identifying
relationship" means in practice — delete the ride and its legs have no meaning, so
they go with it. Contrast `SET_NULL` on `RideLeg.driver`: the leg still happened
even if the driver's account is removed.

**`on_delete=PROTECT` on the locations.** A location that a completed ride refers to
is a financial record. Deleting it would erase where a fare was charged from.
`PROTECT` turns that into an error.

**The `ck_rideleg_origin_differs_from_dest` constraint.** A leg from a place to
itself is not a trip. Catching it in the database rather than in a serializer means
it cannot be written by any path — including a data fix at 2am.

**`fare_estimate` is nullable, `final_fare` is not a column at all.** The estimate
exists before the ride; the final fare is the sum of legs, computed on read.

**`request_time` uses `default=timezone.now`, not `auto_now_add`.** `auto_now_add`
would make the field uneditable, and you need to set it when seeding historical
rides for the demo.

### 2. Migrate (~15 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
python manage.py makemigrations rides
python manage.py migrate
```

Read the generated migration before applying it. Confirm it contains
`UniqueConstraint(fields=["ride", "leg_no"], name="uq_rideleg_ride_legno")` — if it
does not, the constraint block is misplaced.

### 3. Prove the weak entity behaves (~40 min)

Seed the minimum data and exercise a chain. In `manage.py shell`:

```python
from datetime import date
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Passenger, User
from apps.core.enums import RideMode, RideStatus, UserRole
from apps.rides.models import Location, Ride, RideLeg, RideModeLookup

# ── Lookups ────────────────────────────────────────────────────
tricycle, _ = RideModeLookup.objects.get_or_create(
    mode_code=RideMode.TRICYCLE,
    defaults=dict(mode_name="Tricycle", base_fare=Decimal("25.00"),
                  per_km_rate=Decimal("12.00"), seat_capacity=3, is_shared=False),
)
jeepney, _ = RideModeLookup.objects.get_or_create(
    mode_code=RideMode.JEEPNEY,
    defaults=dict(mode_name="Jeepney", base_fare=Decimal("13.00"),
                  per_km_rate=Decimal("2.00"), seat_capacity=20, is_shared=True),
)

# ── A passenger ────────────────────────────────────────────────
u = User.objects.create_user(phone="09170000001", password="test-1234",
                             full_name="Maria Santos", user_role=UserRole.PASSENGER)
pax = Passenger.objects.create(user=u, home_address="12 Rizal St, Poblacion",
                               gcash_number="09170000001")

# ── Locations ──────────────────────────────────────────────────
home = Location.objects.create(street="12 Rizal St", barangay="Poblacion",
                               city="Cabuyao", province="Laguna",
                               latitude=Decimal("14.276400"), longitude=Decimal("121.124500"))
market = Location.objects.create(street="Cabuyao Public Market", barangay="Poblacion",
                                 city="Cabuyao", province="Laguna",
                                 latitude=Decimal("14.279000"), longitude=Decimal("121.126000"))
office = Location.objects.create(street="Nuvali Blvd", barangay="Sto. Domingo",
                                 city="Santa Rosa", province="Laguna",
                                 latitude=Decimal("14.238600"), longitude=Decimal("121.056200"))

# ── A two-leg chain: tricycle then jeepney ─────────────────────
ride = Ride.objects.create(
    passenger=pax, mode=tricycle, pickup_location=home, dropoff_location=office,
    is_trip_chain=True, status=RideStatus.ONGOING,
    fare_estimate=Decimal("60.00"),
)
RideLeg.objects.create(ride=ride, leg_no=1, mode=tricycle, origin_location=home,
                       dest_location=market, fare=Decimal("22.00"),
                       distance_km=Decimal("0.6"), eta_minutes=4)
RideLeg.objects.create(ride=ride, leg_no=2, mode=jeepney, origin_location=market,
                       dest_location=office, fare=Decimal("38.00"),
                       distance_km=Decimal("7.4"), eta_minutes=25)

# ── 1. The denormalized summary recomputes ─────────────────────
ride.recompute_chain_flags()
print("leg_count:", ride.leg_count, "| is_chain:", ride.is_trip_chain)   # 2 | True

# ── 2. final_fare is derived, and adds up ──────────────────────
print("final_fare:", ride.final_fare)                                     # 60.00

# ── 3. Legs come back in order ─────────────────────────────────
print("order:", [l.leg_no for l in ride.legs.all()])                      # [1, 2]

# ── 4. The composite key is enforced ───────────────────────────
try:
    with transaction.atomic():
        RideLeg.objects.create(ride=ride, leg_no=1, mode=tricycle,
                               origin_location=home, dest_location=market,
                               fare=Decimal("1.00"))
    print("*** DUPLICATE LEG ALLOWED — the constraint is missing ***")
except IntegrityError as e:
    print("duplicate leg rejected:", "uq_rideleg_ride_legno" in str(e))

# ── 5. A leg cannot exist without its ride ─────────────────────
print("cascade:", RideLeg.objects.filter(ride=ride).count())              # 2

# ── 6. A leg from a place to itself is rejected ────────────────
try:
    with transaction.atomic():
        RideLeg.objects.create(ride=ride, leg_no=3, mode=tricycle,
                               origin_location=home, dest_location=home,
                               fare=Decimal("1.00"))
    print("*** ZERO-LENGTH LEG ALLOWED ***")
except IntegrityError:
    print("zero-length leg rejected: True")

# ── 7. Deleting the ride takes its legs ────────────────────────
leg_ids = list(ride.legs.values_list("id", flat=True))
ride.delete()
print("legs remaining after ride delete:",
      RideLeg.objects.filter(id__in=leg_ids).count())                     # 0

# Clean up the probe passenger
u.delete()
exit()
```

**Every one of those seven prints is a claim from `schema_listing.md` being checked
against the database.** That is what this step is for.

### 4. Confirm the schema in MySQL (~15 min)

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW CREATE TABLE RIDE_LEG\G"
```

Check for:

- `UNIQUE KEY uq_rideleg_ride_legno (ride_id, leg_no)` ← the composite key
- `FOREIGN KEY (ride_id) REFERENCES RIDE (id)` ← the identifying relationship
- `CHECK (leg_no >= 1)`

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW TABLES LIKE '%RIDE%';"
```

Expected: `RIDE`, `RIDE_LEG`, `RIDE_MODE`.

### 5. Commit (~10 min)

```powershell
Set-Location ..
git add backend/apps/rides/ database/
git commit -m "feat(rides): add LOCATION, RIDE and the RIDE_LEG weak entity"
git push
```

---

## Verify

- [ ] `makemigrations rides` generated one migration, containing `uq_rideleg_ride_legno`
- [ ] `SHOW CREATE TABLE RIDE_LEG` shows the unique key and the FK to RIDE
- [ ] `recompute_chain_flags()` sets `leg_count=2` and `is_trip_chain=True`
- [ ] `ride.final_fare` returns `60.00` and is not a column in `SHOW CREATE TABLE RIDE`
- [ ] Legs read back in `leg_no` order
- [ ] A duplicate `(ride, leg_no)` raises `IntegrityError`
- [ ] A leg whose origin equals its destination raises `IntegrityError`
- [ ] Deleting a ride deletes its legs
- [ ] The `RIDE_LEG` composite-key deviation is recorded in `consistency_report.md`
- [ ] Committed and pushed

---

## Log it

```markdown
**Step 2.04 — rides core models — DONE**

- Added LOCATION (composite address split into 4 columns), RIDE, RIDE_LEG
- RIDE_LEG composite key (ride_id, leg_no) implemented as surrogate id +
  UniqueConstraint uq_rideleg_ride_legno — recorded as a documented deviation
- Added CheckConstraints: leg_no >= 1, origin != destination, ended_at >= request_time
- final_fare is a derived property (sum of legs), not a column
- recompute_chain_flags() maintains leg_count and is_trip_chain from one query
- Verified in MySQL: unique key + FK present; 7 behavioural checks all pass
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `Related model 'rides.SurgePeriod' cannot be resolved` | Step 05 has not run | Expected. Comment out `RideLeg.surge`, or write Step 05's `SurgePeriod` first |
| `Related model 'accounts.Passenger' cannot be resolved` | `apps.accounts` not installed | Check `INSTALLED_APPS` and the `apps.py` name |
| Duplicate `(ride, leg_no)` was allowed | The constraint is missing from the migration | Delete the migration, fix `Meta.constraints`, regenerate |
| `CheckConstraint` rejected at import | Django 6 renamed the `check=` argument | Use `condition=` — `check=` was removed |
| `final_fare` is always `None` | No legs, so `Sum` returns `None` | Expected for a legless ride. Handle it in the serializer, not by defaulting to zero |
| `leg_count` is stale | Legs were added without calling `recompute_chain_flags()` | Call it after any leg write. Phase 3 puts it in the service layer so no view forgets |
| `Cannot delete or update a parent row` | `PROTECT` on a location that a ride references | Correct behaviour. Delete the rides first, or archive the location instead |
| MySQL ignores the `CHECK` | MySQL 8.0.16+ enforces them; older versions parse and ignore | You are on 8.4, so this should not happen. Verify with `SHOW CREATE TABLE` |
| Migrations got tangled across apps | `makemigrations rides` ran before `accounts` | `python manage.py makemigrations` with no app name handles cross-app dependencies |

---

## After this step

A ride and its legs exist. What is still missing is everything that hangs off a
ride: the surge window that priced a leg, the Pakyawan group that shared it, the
position pings that tracked it, and the rating that closed it out.

Next: [05 — Models: rides features](05-models-rides-features.md)
