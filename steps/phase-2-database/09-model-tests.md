# Step 2.09 — Model Tests

| | |
|---|---|
| **Goal** | `pytest` runs against a real MySQL test database; the constraints that matter are asserted by tests rather than assumed; `consistency_report.md`'s claims are checked against the implementation |
| **Day / Time** | Day 14 (Thu 19 Nov) · ~3 hours |
| **Prerequisites** | [Step 2.08](08-migrations-seed-and-admin.md) |
| **Produces** | `backend/pytest.ini`, `backend/tests/` with five test modules, a coverage figure |

---

## What these tests are for

Not coverage. Not "testing" in the abstract.

`database/consistency_report.md` records 61 defects found and fixed *on paper*, and
`docs/plan/design-freeze.md` lists the limitations. Those documents make claims about
what the database enforces. Right now, nothing checks them.

> Every test in this step is a claim from the design document, restated as an
> executable assertion.

That framing is what makes this step worth three hours instead of an hour of
perfunctory smoke tests. A test that says "a leg cannot exist without its ride" is
checking the weak entity. A test that says "the shares sum to the fare" is checking
the Pakyawan split. When one fails in Phase 3, you will know which design decision
broke.

---

## The gotcha that will cost you an hour

Django creates a **separate test database** (`test_sakayph`) and destroys it after.
Your `sakayph` MySQL user was created by the Docker image with privileges on the
`sakayph` database only — so it cannot create `test_sakayph`, and the first `pytest`
run dies with:

```
django.db.utils.OperationalError: (1044, "Access denied for user 'sakayph'@'%'
to database 'test_sakayph'")
```

Fix it properly, so a fresh clone works too. Create `docker/mysql-init/01-grants.sql`:

```sql
-- Runs once, on first initialisation of the MySQL data directory.
-- Django creates and drops `test_sakayph` on every pytest run, so the
-- application user needs rights on it. Backticks escape the underscore,
-- which is otherwise a wildcard in GRANT.
GRANT ALL PRIVILEGES ON `test_sakayph`.* TO 'sakayph'@'%';
FLUSH PRIVILEGES;
```

Mount it in `docker-compose.yml`, under the `mysql` service's `volumes:`:

```yaml
    volumes:
      - mysql_data:/var/lib/mysql
      - ./docker/mysql-init:/docker-entrypoint-initdb.d:ro
```

Init scripts run **only** when the data directory is empty, so apply it:

```powershell
docker compose down -v
docker compose up -d
```

**If you would rather not wipe the volume**, grant it against the running container:

```powershell
"GRANT ALL PRIVILEGES ON ``test_sakayph``.* TO 'sakayph'@'%'; FLUSH PRIVILEGES;" | docker compose exec -T mysql mysql -u root -prootpw
```

The doubled backticks are PowerShell's escape for a literal backtick. Confirm with:

```powershell
docker compose exec mysql mysql -u root -prootpw -e "SHOW GRANTS FOR 'sakayph'@'%';"
```

You should see a line for `test_sakayph`.

---

## Do this

### 1. Configure pytest (~20 min)

Create `backend/pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*

testpaths = tests

addopts =
    -ra
    --strict-markers
    --tb=short
    --cov=apps
    --cov-report=term-missing
    --cov-report=html:htmlcov

markers =
    slow: takes more than a second
    contract: asserts the database schema matches schema_listing.md
```

Two notes on that file:

- **`testpaths = tests`** means run pytest from `backend/`, not the repository root.
  Running from the root picks up nothing and reports "no tests ran", which looks like
  a broken test suite.
- **`--cov=apps`** measures only your code, not Django's. The `term-missing` report
  names the specific lines no test touched, which is far more useful than a
  percentage.

### 2. Write the fixtures (~30 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
New-Item -ItemType Directory -Force tests | Out-Null
New-Item -ItemType File -Force tests\__init__.py | Out-Null
```

Create `backend/tests/conftest.py`:

```python
# backend/tests/conftest.py
"""Shared fixtures.

Plain pytest fixtures rather than factory_boy: the object graph here is small
and the explicit fixtures double as documentation of what a valid row looks
like. factory_boy is worth adding in Phase 5 if the graph grows.
"""

from decimal import Decimal

import pytest

from apps.accounts.models import Driver, LGUUnit, Passenger, User
from apps.core.enums import (
    AccredStatus, PaymentMethod, RideMode, RideStatus, UserRole,
)
from apps.payments.models import PaymentMethodLookup, Wallet
from apps.rides.models import Location, Ride, RideLeg, RideModeLookup


# ── Reference data ─────────────────────────────────────────────

@pytest.fixture
def tricycle(db):
    return RideModeLookup.objects.create(
        mode_code=RideMode.TRICYCLE, mode_name="Tricycle",
        base_fare=Decimal("25.00"), per_km_rate=Decimal("12.00"),
        seat_capacity=3, is_shared=False,
    )


@pytest.fixture
def jeepney(db):
    return RideModeLookup.objects.create(
        mode_code=RideMode.JEEPNEY, mode_name="Jeepney",
        base_fare=Decimal("13.00"), per_km_rate=Decimal("2.00"),
        seat_capacity=20, is_shared=True,
    )


@pytest.fixture
def gcash(db):
    return PaymentMethodLookup.objects.create(
        method_code=PaymentMethod.GCASH, method_name="GCash",
        is_digital=True, gateway_name="GCash",
    )


@pytest.fixture
def cash(db):
    return PaymentMethodLookup.objects.create(
        method_code=PaymentMethod.CASH, method_name="Cash", is_digital=False,
    )


@pytest.fixture
def lgu(db):
    return LGUUnit.objects.create(
        lgu_code="CBO-LAG", lgu_name="City of Cabuyao", province="Laguna",
        region="CALABARZON",
    )


# ── People ─────────────────────────────────────────────────────

@pytest.fixture
def passenger_user(db):
    return User.objects.create_user(
        phone="09171234567", password="sakay-test-1234", full_name="Maria Santos",
        user_role=UserRole.PASSENGER,
    )


@pytest.fixture
def passenger(passenger_user):
    pax = Passenger.objects.create(
        user=passenger_user, home_address="12 Rizal St, Poblacion",
        gcash_number="09171234567",
    )
    Wallet.objects.create(passenger=pax, balance=Decimal("500.00"))
    return pax


@pytest.fixture
def driver_user(db):
    return User.objects.create_user(
        phone="09179876543", password="sakay-test-1234", full_name="Ben Cruz",
        user_role=UserRole.DRIVER,
    )


@pytest.fixture
def driver(driver_user):
    return Driver.objects.create(
        user=driver_user, license_number="N01-23-456789",
        accreditation_status=AccredStatus.VERIFIED, is_online=True,
    )


# ── Places and rides ───────────────────────────────────────────

@pytest.fixture
def locations(db):
    """(home, market, office) — a tricycle hop then a jeepney run."""
    return (
        Location.objects.create(
            street="12 Rizal St", barangay="Poblacion", city="Cabuyao",
            province="Laguna", latitude=Decimal("14.276400"),
            longitude=Decimal("121.124500"),
        ),
        Location.objects.create(
            street="Cabuyao Public Market", barangay="Poblacion", city="Cabuyao",
            province="Laguna", latitude=Decimal("14.279000"),
            longitude=Decimal("121.126000"),
        ),
        Location.objects.create(
            street="Nuvali Blvd", barangay="Sto. Domingo", city="Santa Rosa",
            province="Laguna", latitude=Decimal("14.238600"),
            longitude=Decimal("121.056200"),
        ),
    )


@pytest.fixture
def ride(passenger, tricycle, locations):
    """A two-leg trip chain: tricycle to the market, jeepney onward."""
    home, market, office = locations
    r = Ride.objects.create(
        passenger=passenger, mode=tricycle, pickup_location=home,
        dropoff_location=office, is_trip_chain=True,
        status=RideStatus.ONGOING, fare_estimate=Decimal("60.00"),
    )
    RideLeg.objects.create(
        ride=r, leg_no=1, mode=tricycle, origin_location=home,
        dest_location=market, fare=Decimal("22.00"),
        distance_km=Decimal("0.60"), eta_minutes=4,
    )
    RideLeg.objects.create(
        ride=r, leg_no=2, mode=tricycle, origin_location=market,
        dest_location=office, fare=Decimal("38.00"),
        distance_km=Decimal("7.40"), eta_minutes=25,
    )
    r.recompute_chain_flags()
    r.refresh_from_db()
    return r
```

**Note the `db` fixture.** Every fixture that writes needs it — either directly or
through another fixture that has it. pytest-django's `db` fixture is what creates the
transaction. A fixture that touches the ORM without it raises
`RuntimeError: Database access not allowed`.

### 3. Accounts tests (~25 min)

Create `backend/tests/test_accounts.py`:

```python
"""Accounts-domain tests.

Each test restates a claim from schema_listing.md or consistency_report.md.
"""

import pytest
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import Accreditation, Driver, Passenger, User, Vehicle
from apps.core.enums import AccountStatus, AccredStatus, UserRole


# ── The auth integration ───────────────────────────────────────

def test_phone_is_the_login_identifier(passenger_user):
    """USER has no username column; phone is the USERNAME_FIELD."""
    assert User.USERNAME_FIELD == "phone"
    assert User._meta.label == "accounts.User"
    assert User._meta.db_table == "USER"


def test_password_is_stored_hashed(passenger_user):
    """A plaintext password in the database is the worst bug in the project."""
    assert passenger_user.password.startswith("pbkdf2_sha256$")
    assert "sakay-test-1234" not in passenger_user.password
    assert passenger_user.check_password("sakay-test-1234")


def test_authenticate_by_phone(passenger_user):
    assert authenticate(phone="09171234567", password="sakay-test-1234") == passenger_user


@pytest.mark.parametrize(
    "status,expected",
    [
        (AccountStatus.ACTIVE, True),
        (AccountStatus.SUSPENDED, False),
        (AccountStatus.DEACTIVATED, False),
    ],
)
def test_is_active_is_derived_from_account_status(passenger_user, status, expected):
    """is_active is a property, not a column — the two cannot disagree."""
    passenger_user.account_status = status
    assert passenger_user.is_active is expected


def test_suspended_user_cannot_authenticate(passenger_user):
    passenger_user.account_status = AccountStatus.SUSPENDED
    passenger_user.save(update_fields=["account_status"])
    assert authenticate(phone="09171234567", password="sakay-test-1234") is None


def test_phone_must_be_unique(db):
    User.objects.create_user(phone="09170000001", password="x", full_name="A")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.create_user(phone="09170000001", password="y", full_name="B")


def test_phone_format_is_validated(db):
    """The schema's VARCHAR(15) is not a format check; the validator is."""
    u = User(phone="not-a-number", full_name="X", user_role=UserRole.PASSENGER)
    with pytest.raises(ValidationError):
        u.full_clean()


# ── Class-table inheritance ────────────────────────────────────

def test_subtype_pk_is_the_supertype_pk(passenger, passenger_user):
    """PASSENGER.passenger_id is a FK to USER and the primary key."""
    assert passenger.pk == passenger_user.pk
    assert Passenger._meta.pk.column == "passenger_id"
    assert passenger.user == passenger_user


def test_passenger_profile_requires_passenger_role(driver_user):
    """clean() enforces the discriminator — a DRIVER cannot hold a profile."""
    bad = Passenger(user=driver_user, home_address="X", gcash_number="09179876543")
    with pytest.raises(ValidationError):
        bad.full_clean()


def test_driver_profile_requires_driver_role(passenger_user):
    bad = Driver(user=passenger_user, license_number="N99-99-999999")
    with pytest.raises(ValidationError):
        bad.full_clean()


def test_license_number_is_unique(driver, driver_user):
    other = User.objects.create_user(
        phone="09170000002", password="x", full_name="C", user_role=UserRole.DRIVER
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Driver.objects.create(user=other, license_number=driver.license_number)


# ── Availability and accreditation ─────────────────────────────

def test_driver_availability_needs_online_and_verified(driver):
    assert driver.is_available
    driver.accreditation_status = AccredStatus.PENDING
    assert not driver.is_available
    driver.accreditation_status = AccredStatus.VERIFIED
    driver.is_online = False
    assert not driver.is_available


def test_suspended_driver_is_not_available(driver, driver_user):
    driver_user.account_status = AccountStatus.SUSPENDED
    driver_user.save(update_fields=["account_status"])
    driver.refresh_from_db()
    assert not driver.is_available


def test_one_vehicle_per_driver(driver, tricycle):
    Vehicle.objects.create(driver=driver, mode=tricycle, plate_number="ABC 1234",
                           model="Honda TMX", capacity=3)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Vehicle.objects.create(driver=driver, mode=tricycle,
                                   plate_number="XYZ 9876", model="Kawasaki")


def test_driver_holds_no_accreditation_until_issued(driver):
    """DRIVER -> ACCREDITATION is 1 : 0..*; a new driver holds none."""
    assert driver.accreditations.count() == 0


def test_accreditation_is_unique_per_driver_and_lgu(driver, lgu):
    Accreditation.objects.create(
        driver=driver, lgu=lgu, badge_no="BDG-0001",
        status=AccredStatus.VERIFIED, expiry_date="2027-12-31",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Accreditation.objects.create(
                driver=driver, lgu=lgu, badge_no="BDG-0002",
                status=AccredStatus.VERIFIED, expiry_date="2028-12-31",
            )


def test_passenger_rating_avg_is_derived_not_stored():
    """schema_listing.md marks it DERIVED — so it must not be a column."""
    column_names = {f.column for f in Passenger._meta.get_fields() if hasattr(f, "column")}
    assert "rating_avg" not in column_names
    assert isinstance(Passenger.rating_avg, property)
```

### 4. Rides tests (~35 min)

Create `backend/tests/test_rides.py`:

```python
"""Rides-domain tests — the weak entity, the chain, and Bagyo Mode."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.enums import GroupStatus, RideMode, RideStatus, SurgeTrigger
from apps.rides.models import (
    Location, PakyawanGroup, PassengerPreferredMode, Rating, Ride, RideLeg,
    SurgePeriod, TripTracking,
)


# ── The weak entity ────────────────────────────────────────────

def test_rideleg_unique_on_ride_and_leg_no(ride, tricycle, locations):
    """The documented composite key (ride_id, leg_no), enforced by the DB."""
    home, market, _ = locations
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RideLeg.objects.create(
                ride=ride, leg_no=1, mode=tricycle, origin_location=home,
                dest_location=market, fare=Decimal("1.00"),
            )


def test_rideleg_same_leg_no_on_a_different_ride_is_allowed(ride, passenger, tricycle, locations):
    """Uniqueness is per ride — leg 1 exists on every ride."""
    home, market, _ = locations
    other = Ride.objects.create(
        passenger=passenger, mode=tricycle, pickup_location=home,
        dropoff_location=market, status=RideStatus.REQUESTED,
    )
    RideLeg.objects.create(
        ride=other, leg_no=1, mode=tricycle, origin_location=home,
        dest_location=market, fare=Decimal("25.00"),
    )
    assert RideLeg.objects.filter(leg_no=1).count() == 2


def test_rideleg_cannot_exist_without_a_ride(ride):
    """The identifying relationship: delete the ride, the legs go with it."""
    leg_ids = list(ride.legs.values_list("id", flat=True))
    assert len(leg_ids) == 2
    ride.delete()
    assert RideLeg.objects.filter(id__in=leg_ids).count() == 0


def test_rideleg_leg_no_must_be_positive(ride, tricycle, locations):
    home, market, _ = locations
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RideLeg.objects.create(
                ride=ride, leg_no=0, mode=tricycle, origin_location=home,
                dest_location=market, fare=Decimal("1.00"),
            )


def test_rideleg_origin_must_differ_from_destination(ride, tricycle, locations):
    """A leg from a place to itself is not a trip."""
    home, _, _ = locations
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RideLeg.objects.create(
                ride=ride, leg_no=3, mode=tricycle, origin_location=home,
                dest_location=home, fare=Decimal("1.00"),
            )


def test_rideleg_leg_no_can_repeat_across_rides(ride, passenger, tricycle, locations):
    """Guards against a unique index on leg_no alone."""
    home, market, _ = locations
    r2 = Ride.objects.create(passenger=passenger, mode=tricycle,
                             pickup_location=home, dropoff_location=market)
    RideLeg.objects.create(ride=r2, leg_no=2, mode=tricycle, origin_location=home,
                           dest_location=market, fare=Decimal("9.00"))
    assert RideLeg.objects.filter(leg_no=2).count() == 2


# ── The chain ──────────────────────────────────────────────────

def test_legs_come_back_in_order(ride):
    assert [leg.leg_no for leg in ride.legs.all()] == [1, 2]


def test_final_fare_sums_the_legs(ride):
    """DERIVED — computed from the legs, never stored."""
    assert ride.final_fare == Decimal("60.00")
    column_names = {f.column for f in Ride._meta.get_fields() if hasattr(f, "column")}
    assert "final_fare" not in column_names


def test_final_fare_tracks_a_leg_change(ride):
    leg = ride.legs.get(leg_no=2)
    leg.fare = Decimal("45.00")
    leg.save(update_fields=["fare"])
    assert ride.final_fare == Decimal("67.00")


def test_recompute_chain_flags_sets_count_and_flag(ride):
    assert ride.leg_count == 2
    assert ride.is_trip_chain is True


def test_single_leg_ride_is_not_a_chain(passenger, tricycle, locations):
    home, market, _ = locations
    r = Ride.objects.create(passenger=passenger, mode=tricycle,
                            pickup_location=home, dropoff_location=market)
    RideLeg.objects.create(ride=r, leg_no=1, mode=tricycle, origin_location=home,
                           dest_location=market, fare=Decimal("25.00"))
    r.recompute_chain_flags()
    r.refresh_from_db()
    assert r.leg_count == 1
    assert r.is_trip_chain is False


def test_ended_at_cannot_precede_request_time(passenger, tricycle, locations):
    home, market, _ = locations
    r = Ride.objects.create(passenger=passenger, mode=tricycle,
                            pickup_location=home, dropoff_location=market)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Ride.objects.filter(pk=r.pk).update(
                ended_at=r.request_time - timedelta(hours=1)
            )


# ── Bagyo Mode ─────────────────────────────────────────────────

def test_surge_window_is_current_only_inside_it(db):
    now = timezone.now()
    past = SurgePeriod.objects.create(
        surge_label="Signal No. 2", trigger_type=SurgeTrigger.WEATHER,
        multiplier=Decimal("1.50"), starts_at=now - timedelta(hours=5),
        ends_at=now - timedelta(hours=1),
    )
    assert not past.is_current


def test_inactive_surge_is_not_current_even_inside_its_window(db):
    """An administratively ended surge stops applying immediately."""
    now = timezone.now()
    s = SurgePeriod.objects.create(
        surge_label="Cancelled advisory", trigger_type=SurgeTrigger.LGU_ADVISORY,
        multiplier=Decimal("1.30"), starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(hours=1), is_active=False,
    )
    assert not s.is_current
    assert SurgePeriod.active_at() is None


def test_active_at_returns_the_highest_multiplier(db):
    """Overlapping windows are real — a national signal and a city advisory."""
    now = timezone.now()
    SurgePeriod.objects.create(
        surge_label="Signal No. 1", trigger_type=SurgeTrigger.WEATHER,
        multiplier=Decimal("1.25"), starts_at=now - timedelta(minutes=30),
        ends_at=now + timedelta(hours=2),
    )
    SurgePeriod.objects.create(
        surge_label="Demand spike", trigger_type=SurgeTrigger.DEMAND,
        multiplier=Decimal("1.80"), starts_at=now - timedelta(minutes=5),
        ends_at=now + timedelta(minutes=30),
    )
    assert SurgePeriod.active_at().surge_label == "Demand spike"


def test_surge_window_must_end_after_it_starts(db):
    now = timezone.now()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SurgePeriod.objects.create(
                surge_label="Inverted", trigger_type=SurgeTrigger.MANUAL,
                multiplier=Decimal("2.00"), starts_at=now,
                ends_at=now - timedelta(hours=1),
            )


def test_surge_multiplier_cannot_be_below_one(db):
    """Bagyo Mode is a surcharge; a discount is a different feature."""
    now = timezone.now()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SurgePeriod.objects.create(
                surge_label="Discount", trigger_type=SurgeTrigger.MANUAL,
                multiplier=Decimal("0.50"), starts_at=now,
                ends_at=now + timedelta(hours=1),
            )


def test_leg_records_the_surge_it_was_priced_under(ride, locations, tricycle):
    """A fare stays explainable after the window closes."""
    now = timezone.now()
    surge = SurgePeriod.objects.create(
        surge_label="Signal No. 2", trigger_type=SurgeTrigger.WEATHER,
        multiplier=Decimal("1.50"), starts_at=now - timedelta(minutes=5),
        ends_at=now + timedelta(hours=3),
    )
    leg = ride.legs.get(leg_no=1)
    leg.surge = surge
    leg.save(update_fields=["surge"])
    assert ride.legs.get(leg_no=1).surge.multiplier == Decimal("1.50")


# ── Pakyawan ───────────────────────────────────────────────────

def test_pakyawan_group_is_one_per_ride(ride):
    PakyawanGroup.objects.create(ride=ride, direction="Cabuyao → Sta. Rosa", max_seats=4)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PakyawanGroup.objects.create(ride=ride, direction="duplicate", max_seats=2)


def test_pakyawan_seats_cannot_exceed_capacity(ride):
    grp = PakyawanGroup.objects.create(ride=ride, direction="X → Y", max_seats=4)
    for _ in range(4):
        assert grp.add_seat() is True
    assert grp.add_seat() is False
    grp.refresh_from_db()
    assert grp.matched_seats == 4
    assert grp.group_status == GroupStatus.FULL
    assert grp.is_full


def test_pakyawan_capacity_is_enforced_by_the_database(ride):
    """add_seat() is the friendly path; the CHECK is the guarantee."""
    grp = PakyawanGroup.objects.create(ride=ride, direction="X → Y", max_seats=2)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PakyawanGroup.objects.filter(pk=grp.pk).update(matched_seats=99)


def test_seats_available_decreases(ride):
    grp = PakyawanGroup.objects.create(ride=ride, direction="X → Y", max_seats=3)
    assert grp.seats_available == 3
    grp.add_seat()
    assert grp.seats_available == 2


# ── Preferred modes ────────────────────────────────────────────

def test_preferred_mode_is_unique_per_passenger(passenger, tricycle):
    PassengerPreferredMode.objects.create(passenger=passenger, mode=tricycle,
                                          preferred_rank=1)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PassengerPreferredMode.objects.create(passenger=passenger, mode=tricycle,
                                                  preferred_rank=9)


def test_preferred_mode_names_come_back_in_rank_order(passenger, tricycle, jeepney):
    PassengerPreferredMode.objects.create(passenger=passenger, mode=jeepney,
                                          preferred_rank=2)
    PassengerPreferredMode.objects.create(passenger=passenger, mode=tricycle,
                                          preferred_rank=1)
    assert passenger.preferred_mode_names == ["Tricycle", "Jeepney"]


# ── Saan ang Jeep? ─────────────────────────────────────────────

def test_tracking_pings_are_append_only_and_ordered(ride):
    now = timezone.now()
    for i in range(3):
        TripTracking.objects.create(
            ride=ride, latitude=Decimal("14.276400") + Decimal(i) / 1000,
            longitude=Decimal("121.124500"), recorded_at=now + timedelta(seconds=i * 10),
        )
    assert TripTracking.objects.filter(ride=ride).count() == 3
    assert TripTracking.latest_for(ride).recorded_at == now + timedelta(seconds=20)


def test_tracking_trail_is_oldest_first(ride):
    """Leaflet draws a polyline in the order given, so the trail is reversed."""
    now = timezone.now()
    for i in range(3):
        TripTracking.objects.create(
            ride=ride, latitude=Decimal("14.27"), longitude=Decimal("121.12"),
            recorded_at=now + timedelta(seconds=i * 10),
        )
    seconds = [p.recorded_at for p in TripTracking.trail_for(ride)]
    assert seconds == sorted(seconds)


def test_tracking_uses_a_bigint_key():
    """The only non-UUID key in the schema — a high-volume time series."""
    assert TripTracking._meta.pk.name == "track_id"
    assert TripTracking._meta.pk.get_internal_type() == "BigAutoField"


# ── Rating: the unary relationship ─────────────────────────────

def test_rating_has_two_foreign_keys_to_user():
    """The unary relationship needs two distinct related_names."""
    fk_targets = {
        f.name: f.related_model._meta.label
        for f in Rating._meta.get_fields()
        if f.is_relation and f.many_to_one
    }
    assert fk_targets["rater_user"] == "accounts.User"
    assert fk_targets["ratee_user"] == "accounts.User"


def test_rating_updates_the_cached_driver_average(ride, passenger_user, driver_user, driver):
    Rating.objects.create(ride=ride, rater_user=passenger_user,
                          ratee_user=driver_user, stars=5)
    driver.refresh_from_db()
    assert driver.rating == Decimal("5.0")


def test_driver_rating_averages_across_ratings(ride, passenger_user, driver_user, driver, passenger, tricycle, locations):
    home, market, _ = locations
    other = Ride.objects.create(passenger=passenger, mode=tricycle,
                                pickup_location=home, dropoff_location=market)
    Rating.objects.create(ride=ride, rater_user=passenger_user,
                          ratee_user=driver_user, stars=4)
    Rating.objects.create(ride=other, rater_user=passenger_user,
                          ratee_user=driver_user, stars=5)
    driver.refresh_from_db()
    assert driver.rating == Decimal("4.5")


def test_nobody_rates_themselves(ride, passenger_user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Rating.objects.create(ride=ride, rater_user=passenger_user,
                                  ratee_user=passenger_user, stars=5)


def test_one_rating_per_rater_per_ride(ride, passenger_user, driver_user):
    Rating.objects.create(ride=ride, rater_user=passenger_user,
                          ratee_user=driver_user, stars=5)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Rating.objects.create(ride=ride, rater_user=passenger_user,
                                  ratee_user=driver_user, stars=1)


def test_stars_are_bounded(ride, passenger_user, driver_user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Rating.objects.create(ride=ride, rater_user=passenger_user,
                                  ratee_user=driver_user, stars=9)


def test_passenger_rating_avg_averages_received_ratings(ride, passenger_user, driver_user, passenger):
    Rating.objects.create(ride=ride, rater_user=driver_user,
                          ratee_user=passenger_user, stars=4)
    assert passenger.rating_avg == 4.0


def test_unrated_passenger_returns_none_not_zero(passenger):
    """"Unrated" and "rated zero" must stay distinguishable."""
    assert passenger.rating_avg is None
```

### 5. Payments and safety tests (~35 min)

Create `backend/tests/test_payments.py`:

```python
"""Payments-domain tests — the split, the ledger and the 1:0..1 constraints."""

from decimal import ROUND_HALF_UP, Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.core.enums import PaymentStatus, PayoutStatus, TxnType
from apps.payments.models import (
    DriverPayout, FareShare, Payment, Receipt, Wallet, WalletTxn,
)
from apps.rides.models import PakyawanGroup


@pytest.fixture
def payment(ride, passenger, gcash):
    return Payment.objects.create(
        ride=ride, payer=passenger, method=gcash, amount=ride.final_fare,
        status=PaymentStatus.COMPLETED,
    )


def test_one_payment_per_ride(ride, passenger, gcash, cash):
    """PAYMENT.ride is NOT NULL + UNIQUE — the 1 : 0..1."""
    Payment.objects.create(ride=ride, payer=passenger, method=gcash,
                           amount=Decimal("60.00"))
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Payment.objects.create(ride=ride, payer=passenger, method=cash,
                                   amount=Decimal("60.00"))


def test_cash_payment_needs_no_wallet(ride, passenger, cash):
    """PAYMENT -> WALLET is 0..1 : 0..*; cash bypasses the wallet."""
    p = Payment.objects.create(ride=ride, payer=passenger, method=cash,
                               amount=Decimal("60.00"))
    assert p.wallet is None


def test_wallet_balance_cannot_go_negative(passenger):
    """The safety net for every money bug."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Wallet.objects.filter(pk=passenger.wallet.pk).update(balance=Decimal("-1.00"))


def test_wallet_txn_records_the_running_balance(passenger, payment):
    w = passenger.wallet
    w.balance = w.balance - Decimal("33.34")
    w.save(update_fields=["balance", "updated_at"])
    txn = WalletTxn.objects.create(wallet=w, payment=payment, txn_type=TxnType.DEDUCT,
                                   amount=Decimal("33.34"), balance_after=w.balance,
                                   gateway_ref="SIM-W-0001")
    w.refresh_from_db()
    assert txn.balance_after == w.balance == Decimal("466.66")


def test_wallet_with_ledger_entries_cannot_be_deleted(passenger, payment):
    """The ledger is the audit trail — PROTECT, not CASCADE."""
    w = passenger.wallet
    WalletTxn.objects.create(wallet=w, payment=payment, txn_type=TxnType.DEDUCT,
                             amount=Decimal("10.00"), balance_after=Decimal("490.00"))
    with pytest.raises(Exception):
        with transaction.atomic():
            w.delete()


def test_txn_type_has_no_payout_value():
    """Driver earnings are not a passenger-wallet transaction."""
    assert "PAYOUT" not in TxnType.values
    assert set(TxnType.values) == {"TOPUP", "DEDUCT", "REFUND"}


def test_fare_share_is_unique_per_payment_and_passenger(payment, passenger, ride):
    grp = PakyawanGroup.objects.create(ride=ride, direction="X → Y", max_seats=4)
    FareShare.objects.create(payment=payment, passenger=passenger, group=grp,
                             passenger_count=1, share_amount=Decimal("60.00"))
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            FareShare.objects.create(payment=payment, passenger=passenger, group=grp,
                                     passenger_count=1, share_amount=Decimal("1.00"))


def test_fare_share_amount_cannot_be_negative(payment, passenger, ride):
    grp = PakyawanGroup.objects.create(ride=ride, direction="X → Y", max_seats=4)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            FareShare.objects.create(payment=payment, passenger=passenger, group=grp,
                                     passenger_count=2, share_amount=Decimal("-5.00"))


def split_fare(total: Decimal, count: int) -> list[Decimal]:
    """The Pakyawan split, with the rounding remainder pushed onto one share.

    ROUND_HALF_UP on each share alone leaves a remainder — 100.00 / 3 gives
    99.99 — so the leftover centavo has to go somewhere or the shares never
    total the fare. This helper is what Phase 3's FareCalculator will use;
    writing it here first means the rule is tested before it is relied on.
    """
    base = (total / Decimal(count)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    shares = [base] * count
    shares[0] += total - (base * count)
    return shares


@pytest.mark.parametrize("count", [1, 2, 3, 4, 7])
def test_split_sums_to_the_fare_exactly(count):
    """The Pakyawan invariant: the shares must total the fare, exactly."""
    total = Decimal("60.00")
    shares = split_fare(total, count)
    assert sum(shares) == total, f"{count}-way split of {total} gives {sum(shares)}"
    assert all(s >= 0 for s in shares)
    assert len(shares) == count


@pytest.mark.parametrize("count", [3, 7, 11])
def test_naive_rounding_would_lose_a_centavo(count):
    """The bug the remainder-push exists to prevent.

    If each share is rounded independently the total falls short. This test
    documents why split_fare is written the way it is — remove the remainder
    push and both this and the test above fail.
    """
    total = Decimal("100.00")
    base = (total / Decimal(count)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert base * count != total, "pick a total that does not divide evenly"


def test_split_writes_one_share_per_passenger(payment, passenger, ride):
    """FARE_SHARE is unique on (payment, passenger), so a 3-way split needs
    three distinct passengers — which is the whole point of the table."""
    from apps.accounts.models import Passenger, User
    from apps.core.enums import UserRole

    others = []
    for i in range(2):
        u = User.objects.create_user(
            phone=f"0917000009{i}", password="x", full_name=f"Pasahero {i}",
            user_role=UserRole.PASSENGER,
        )
        others.append(Passenger.objects.create(
            user=u, home_address="X", gcash_number=f"0917000009{i}",
        ))

    grp = PakyawanGroup.objects.create(ride=ride, direction="X → Y", max_seats=4)
    everyone = [passenger, *others]
    shares = split_fare(payment.amount, len(everyone))

    for pax, amount in zip(everyone, shares):
        FareShare.objects.create(
            payment=payment, passenger=pax, group=grp,
            passenger_count=len(everyone), share_amount=amount,
        )

    stored = list(payment.shares.values_list("share_amount", flat=True))
    assert len(stored) == 3
    assert sum(stored) == payment.amount


def test_receipt_number_is_sequential(payment):
    first = Receipt.objects.create(payment=payment, total_amount=payment.amount,
                                   receipt_no=Receipt.next_receipt_no())
    assert first.receipt_no.endswith("-0001")
    assert Receipt.next_receipt_no().endswith("-0002")


def test_receipt_total_is_a_snapshot(payment):
    """A receipt must not move if the payment is later adjusted."""
    r = Receipt.objects.create(payment=payment, total_amount=payment.amount,
                               receipt_no=Receipt.next_receipt_no())
    payment.amount = Decimal("999.00")
    payment.save(update_fields=["amount"])
    r.refresh_from_db()
    assert r.total_amount == Decimal("60.00")


def test_one_receipt_per_payment(payment):
    Receipt.objects.create(payment=payment, total_amount=payment.amount,
                           receipt_no=Receipt.next_receipt_no())
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Receipt.objects.create(payment=payment, total_amount=payment.amount,
                                   receipt_no="SKY-19700101-9999")


def test_driver_payout_defaults_to_requested(driver, gcash):
    p = DriverPayout.objects.create(driver=driver, method=gcash,
                                    amount=Decimal("90.00"), gateway_ref="SIM-P-0001")
    assert p.status == PayoutStatus.REQUESTED
    assert p.is_settled is False


def test_payout_is_not_a_wallet_transaction(driver, gcash):
    """WALLET is passenger-scoped, so a payout needs its own table."""
    payout = DriverPayout.objects.create(driver=driver, method=gcash,
                                         amount=Decimal("90.00"))
    assert payout._meta.db_table == "DRIVER_PAYOUT"
    assert not hasattr(payout, "wallet")
```

Create `backend/tests/test_safety.py`:

```python
"""Safety-domain tests — the SOS fan-out and its associative entity."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.enums import DeliveryStatus, SOSStatus
from apps.safety.models import SOSAlert, SOSNotification, TrustedContact


@pytest.fixture
def contacts(passenger):
    return [
        TrustedContact.objects.create(passenger=passenger, contact_name="Mama",
                                      contact_mobile="09171111111",
                                      relationship="Mother"),
        TrustedContact.objects.create(passenger=passenger, contact_name="Ate Joy",
                                      contact_mobile="09172222222",
                                      relationship="Sister"),
        TrustedContact.objects.create(passenger=passenger,
                                      contact_name="Barangay Hall",
                                      contact_mobile="09173333333",
                                      relationship="Barangay"),
    ]


@pytest.fixture
def alert(ride, passenger_user):
    return SOSAlert.objects.create(
        ride=ride, raised_by=passenger_user, alert_type="harassment",
        alert_lat=Decimal("14.261000"), alert_long=Decimal("121.115000"),
    )


def test_trusted_contact_mobile_is_unique_per_passenger(passenger, contacts):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TrustedContact.objects.create(passenger=passenger, contact_name="Dup",
                                          contact_mobile="09171111111")


def test_alert_snapshots_the_position(alert):
    """The position at trigger time is evidence; it must not track later."""
    assert alert.coordinates == (14.261, 121.115)


def test_one_sos_per_ride(alert, ride, passenger_user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SOSAlert.objects.create(ride=ride, raised_by=passenger_user,
                                    alert_type="second",
                                    alert_lat=Decimal("14.26"),
                                    alert_long=Decimal("121.11"))


def test_fan_out_creates_one_notification_per_contact(alert, contacts):
    for c in contacts:
        SOSNotification.objects.create(alert=alert, contact=c)
    assert alert.notifications.count() == 3
    assert alert.notified_count == 0  # all still SENT


def test_notification_is_unique_per_alert_and_contact(alert, contacts):
    SOSNotification.objects.create(alert=alert, contact=contacts[0])
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SOSNotification.objects.create(alert=alert, contact=contacts[0])


def test_notified_count_counts_only_delivered(alert, contacts):
    for c in contacts:
        SOSNotification.objects.create(alert=alert, contact=c)
    alert.notifications.filter(contact__in=contacts[:2]).update(
        delivery_status=DeliveryStatus.FAILED
    )
    alert.notifications.get(contact=contacts[2]).mark_delivered()
    assert alert.notified_count == 1
    assert alert.notifications.filter(delivery_status=DeliveryStatus.FAILED).count() == 2


def test_alert_is_open_until_resolved(alert):
    assert alert.is_open
    alert.status = SOSStatus.RESOLVED
    alert.resolved_at = timezone.now()
    alert.save(update_fields=["status", "resolved_at"])
    assert not alert.is_open
    assert alert.response_seconds is not None


def test_open_alert_has_no_response_time(alert):
    assert alert.response_seconds is None


def test_resolved_at_cannot_precede_triggered_at(alert):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SOSAlert.objects.filter(pk=alert.pk).update(
                triggered_at=timezone.now(),
                resolved_at=timezone.now() - timedelta(hours=1),
            )


def test_deleting_a_contact_removes_its_notification(alert, contacts):
    """CASCADE here is deliberate — see the model docstring."""
    SOSNotification.objects.create(alert=alert, contact=contacts[0])
    contacts[0].delete()
    assert alert.notifications.count() == 0


def test_alert_survives_a_ride_delete_attempt(alert, ride):
    """SOSAlert.ride is PROTECT — an alert is evidence."""
    with pytest.raises(Exception):
        with transaction.atomic():
            ride.delete()
```

### 6. The schema contract test (~30 min)

This is the test file that makes the others meaningful. It asserts that the database
*structure* matches `schema_listing.md` — the part no ordinary unit test covers.

Create `backend/tests/test_schema_contract.py`:

```python
"""Schema contract tests.

Asserts that the migrated database matches database/schema_listing.md and the
design decisions recorded in consistency_report.md. If one of these fails, the
document and the database have drifted apart — which is the one failure mode a
design-first project cannot tolerate.
"""

import pytest
from django.db import connection

pytestmark = pytest.mark.contract


# ── The 27 tables ──────────────────────────────────────────────

# Written out rather than derived from the models, so that a typo in a
# model's db_table is caught instead of being compared against itself.
DOCUMENTED_TABLES = [
    "ACCREDITATION", "CANCELLATION", "DRIVER", "DRIVER_PAYOUT", "FARE_SHARE",
    "LGU_UNIT", "LOCATION", "PAKYAWAN_GROUP", "PASSENGER",
    "PASSENGER_PREFERRED_MODE", "PAYMENT", "PAYMENT_METHOD", "PLATFORM_CONFIG",
    "RATING", "RECEIPT",
    "RIDE", "RIDE_LEG", "RIDE_MODE", "SOS_ALERT", "SOS_NOTIFICATION",
    "SURGE_PERIOD", "TRIP_TRACKING", "TRUSTED_CONTACT", "USER", "VEHICLE",
    "WALLET", "WALLET_TXN",
]


def _app_tables() -> set[str]:
    """Table names in the current schema, excluding Django's own."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name NOT LIKE 'django\\_%'
              AND table_name NOT LIKE 'auth\\_%'
            """
        )
        return {row[0] for row in cur.fetchall()}


def test_all_documented_tables_exist():
    assert len(DOCUMENTED_TABLES) == 27, "27 tables: the original 26 plus PLATFORM_CONFIG (D-62)"
    missing = set(DOCUMENTED_TABLES) - _app_tables()
    assert not missing, f"documented but not migrated: {sorted(missing)}"


def test_no_undocumented_tables_exist():
    """Catches a model whose db_table was never added to the design."""
    extra = _app_tables() - set(DOCUMENTED_TABLES)
    assert not extra, f"migrated but not documented: {sorted(extra)}"


# ── Composite keys implemented as UNIQUE constraints ───────────

def _unique_indexes(table: str) -> set[frozenset]:
    """Each unique index in `table`, as a frozenset of column names."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT index_name, GROUP_CONCAT(column_name ORDER BY seq_in_index)
            FROM information_schema.statistics
            WHERE table_schema = DATABASE() AND table_name = %s AND non_unique = 0
            GROUP BY index_name
            """,
            [table],
        )
        return {frozenset(cols.split(",")) for _, cols in cur.fetchall()}


@pytest.mark.parametrize(
    "table,columns,constraint",
    [
        ("RIDE_LEG", {"ride_id", "leg_no"}, "uq_rideleg_ride_legno"),
        ("FARE_SHARE", {"payment_id", "passenger_id"}, "uq_fareshare_payment_passenger"),
        ("SOS_NOTIFICATION", {"alert_id", "contact_id"}, "uq_sosnotif_alert_contact"),
        ("PASSENGER_PREFERRED_MODE", {"passenger_id", "mode_code"},
         "uq_prefmode_passenger_mode"),
    ],
)
def test_composite_key_is_enforced(table, columns, constraint):
    """The four documented composite keys, implemented as unique indexes.

    This is the deviation recorded in consistency_report.md: Django has no
    composite primary key, so uniqueness carries the guarantee instead.
    """
    indexes = _unique_indexes(table)
    assert frozenset(columns) in indexes, (
        f"{table} has no UNIQUE index on {sorted(columns)}; found {indexes}"
    )


@pytest.mark.parametrize(
    "table,columns",
    [
        ("USER", {"phone"}),
        ("PAYMENT", {"ride_id"}),
        ("RECEIPT", {"payment_id"}),
        ("PAKYAWAN_GROUP", {"ride_id"}),
        ("SOS_ALERT", {"ride_id"}),
        ("CANCELLATION", {"ride_id"}),
        ("WALLET", {"passenger_id"}),
        ("VEHICLE", {"driver_id"}),
        ("DRIVER", {"license_number"}),
        ("ACCREDITATION", {"badge_no"}),
    ],
)
def test_one_to_one_and_unique_columns(table, columns):
    """Every 1 : 0..1 in the schema is a UNIQUE constraint in the database."""
    assert frozenset(columns) in _unique_indexes(table), (
        f"{table} is missing UNIQUE on {sorted(columns)}"
    )


# ── Enumerated columns are wide enough ─────────────────────────

@pytest.mark.parametrize(
    "table,column,width",
    [
        ("USER", "user_role", 12),
        ("USER", "account_status", 12),
        ("RIDE", "status", 16),
        ("RIDE_LEG", "status", 16),
        ("DRIVER", "accreditation_status", 12),
        ("SURGE_PERIOD", "trigger_type", 12),
        ("PAYMENT", "status", 16),
        ("WALLET_TXN", "txn_type", 12),
        ("SOS_ALERT", "status", 12),
        ("SOS_NOTIFICATION", "delivery_status", 12),
        ("PAKYAWAN_GROUP", "group_status", 12),
        ("DRIVER_PAYOUT", "status", 12),
    ],
)
def test_enum_column_width_matches_the_schema(table, column, width):
    """A column one character too narrow silently truncates a status value."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT character_maximum_length FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
            """,
            [table, column],
        )
        row = cur.fetchone()
    assert row is not None, f"{table}.{column} does not exist"
    assert row[0] == width, f"{table}.{column} is VARCHAR({row[0]}), expected {width}"


def test_every_enum_value_fits_its_column():
    """The width table in schema_listing.md, checked against the enum itself."""
    from apps.core import enums

    widths = {
        "UserRole": 12, "AccountStatus": 12, "RideMode": 12, "RideStatus": 16,
        "PaymentMethod": 12, "PaymentStatus": 16, "AccredStatus": 12,
        "SOSStatus": 12, "PayoutStatus": 12, "SurgeTrigger": 12, "TxnType": 12,
        "GroupStatus": 12, "DeliveryStatus": 12,
    }
    for name, width in widths.items():
        enum_cls = getattr(enums, name)
        longest = max(len(v) for v in enum_cls.values)
        assert longest <= width, (
            f"{name}.{max(enum_cls.values, key=len)} is {longest} chars "
            f"but the column is VARCHAR({width})"
        )


# ── Money is never a float ─────────────────────────────────────

def test_no_float_columns_for_money():
    """A fare stored as a float rounds wrong in ways you cannot explain."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND (column_name LIKE '%%fare%%' OR column_name LIKE '%%amount%%'
                   OR column_name LIKE '%%balance%%' OR column_name LIKE '%%rate%%'
                   OR column_name LIKE '%%fee%%')
            """
        )
        offenders = [
            (t, c, d) for t, c, d in cur.fetchall()
            if d in ("float", "double", "real")
        ]
    assert not offenders, f"money columns stored as float: {offenders}"


# ── Encoding ───────────────────────────────────────────────────

def test_connection_charset_is_utf8mb4():
    """Tagalog diacritics and the mode emoji both need 4-byte UTF-8."""
    with connection.cursor() as cur:
        cur.execute("SHOW VARIABLES LIKE 'character_set_connection'")
        assert cur.fetchone()[1] == "utf8mb4"


def test_non_ascii_round_trips(db):
    """The ñ in Biñan and the peso sign in a fare label."""
    from apps.accounts.models import LGUUnit

    LGUUnit.objects.create(lgu_code="BIN-LAG", lgu_name="City of Biñan",
                           province="Laguna", region="CALABARZON")
    assert LGUUnit.objects.get(lgu_code="BIN-LAG").lgu_name == "City of Biñan"


# ── Soft checks against the design documents ───────────────────

def test_rating_points_at_user_twice():
    """The unary relationship, in the DDL."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, referenced_table_name
            FROM information_schema.key_column_usage
            WHERE table_schema = DATABASE() AND table_name = 'RATING'
              AND referenced_table_name IS NOT NULL
            """
        )
        refs = dict(cur.fetchall())
    assert refs.get("rater_user_id") == "USER"
    assert refs.get("ratee_user_id") == "USER"


def test_passenger_pk_is_also_a_foreign_key():
    """Class-table inheritance: the subtype PK is the supertype FK."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, referenced_table_name
            FROM information_schema.key_column_usage
            WHERE table_schema = DATABASE() AND table_name = 'PASSENGER'
              AND referenced_table_name IS NOT NULL
            """
        )
        refs = dict(cur.fetchall())
    assert refs.get("passenger_id") == "USER"


def test_driver_earnings_are_not_in_the_passenger_wallet():
    """TxnType has no PAYOUT, and DRIVER_PAYOUT exists instead."""
    from apps.core.enums import TxnType

    assert "PAYOUT" not in TxnType.values
    assert "DRIVER_PAYOUT" in _app_tables()
```

### 7. Run them (~20 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
pytest
```

Expected shape:

```
tests/test_accounts.py ....................            [ 32%]
tests/test_payments.py ...............                 [ 56%]
tests/test_rides.py ...............................    [ 86%]
tests/test_safety.py ..........                        [ 97%]
tests/test_schema_contract.py ...                      [100%]

---------- coverage: platform win32, python 3.14 ----------
Name                                 Stmts   Miss  Cover   Missing
------------------------------------------------------------------
apps/accounts/models.py                128      6    95%   41-44, 210
...
TOTAL                                  ...
```

**Read the `Missing` column, not the percentage.** A line in `Missing` that is a
constraint or a branch is a claim nothing tests.

Useful invocations:

```powershell
pytest -q                                  # quiet
pytest tests/test_rides.py -v              # one module, verbose
pytest -k "surge or pakyawan"              # by keyword
pytest -m contract                         # only the schema contract tests
pytest --no-cov -q                         # skip coverage for speed
pytest -x                                  # stop at the first failure
```

### 8. Record the result and tag (~15 min)

```powershell
Set-Location ..
git add backend/ docker/ requirements/
git commit -m "test(db): add model and schema-contract tests for all 27 tables"
git push
```

Add a row to `steps/PROGRESS.md` with the test count and coverage figure, and note in
`docs/plan/design-freeze.md` that the limitations are now covered by tests where they
can be.

---

## Verify

```powershell
Set-Location backend
pytest -q
pytest -m contract -v
```

- [ ] `pytest` collects and runs with no errors
- [ ] The schema contract tests confirm 27 tables
- [ ] All four composite keys have a matching UNIQUE index
- [ ] Every 1 : 0..1 column has a UNIQUE index
- [ ] Enum column widths match `schema_listing.md`
- [ ] No money column is a float
- [ ] The utf8mb4 round-trip passes
- [ ] The `Missing` column has been read, not just the percentage
- [ ] Coverage is recorded in `steps/PROGRESS.md`
- [ ] Committed and pushed

---

## Log it

```markdown
**Step 2.09 — model tests — DONE**

- Added pytest.ini (DJANGO_SETTINGS_MODULE, coverage over apps/, contract marker)
- Added docker/mysql-init/01-grants.sql so the app user can create test_sakayph
- Wrote tests/conftest.py with fixtures for reference data, people, places, a
  two-leg chain
- test_accounts, test_rides, test_payments, test_safety: constraints from
  consistency_report.md restated as assertions
- test_schema_contract: 27 tables, 4 composite keys, 10 unique columns,
  12 enum widths, no float money columns, utf8mb4 round-trip, unary FK check
- **Tests:** <n> passed | **Coverage:** <n>%
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `Access denied ... 'test_sakayph'` | The app user cannot create the test database | Section at the top of this step — grant or init script |
| `no tests ran` | pytest run from the repository root | `Set-Location backend` first |
| `RuntimeError: Database access not allowed` | A fixture touches the ORM without the `db` fixture | Add `db` to that fixture's parameters |
| `django.core.exceptions.ImproperlyConfigured` | `DJANGO_SETTINGS_MODULE` not found | `pytest.ini` must be in `backend/`, next to `manage.py` |
| An `IntegrityError` test fails the next test too | The failed statement poisoned the outer transaction | Wrap the failing call in `with transaction.atomic():` — every test here does |
| `IntegrityError` not raised | The constraint is missing from the migration | `SHOW CREATE TABLE` the table; fix `Meta.constraints` and re-migrate |
| `test_no_undocumented_tables_exist` fails on `PLATFORM_CONFIG` | The model exists but is missing from `DOCUMENTED_TABLES` | Add it to the list — it is table 27 as of **D-62**. The list is the design; the model must match it, not the reverse |
| `test_enum_column_width_matches_the_schema` fails | A model's `max_length` differs from the schema | Fix the model, migrate. **Do not change the test to match** |
| Coverage below 70% | The `Missing` lines are constraints and branches | Read them. A constraint with no test is the finding |
| Tests slow | MySQL round-trips per test | Add `--reuse-db` while iterating; the first run creates the schema, later runs reuse it |
| `--reuse-db` gives stale-schema failures | Models changed since the test DB was built | `pytest --create-db` |
| `AttributeError: module 'timezone' has no attribute 'timedelta'` | `timedelta` lives in `datetime` | `from datetime import timedelta` — Django's timezone module re-exports it, but importing it properly is clearer |

---

## After this step

**Phase 2 is complete and milestone M2 is met.** The evidence:

- 27 tables migrated from a design that was audited before a line of code was written
- Reference data seeded idempotently, so a fresh clone works in two commands
- Every model inspectable in the admin
- The design document's claims enforced by tests rather than assumed
- Three design changes recorded rather than made silently

```powershell
git tag -a v0.1.0 -m "Database and domain model complete"   # if not already tagged
git push origin v0.1.0
```

**The next phase is where the project becomes visible.** Phase 3 turns these models
into an API: serializers, viewsets, JWT authentication, the matching engine, the fare
calculator, WebSocket consumers for live tracking, and the `simulate_driver` command
that makes the tracking demo actually move.

Next: **Phase 3 — Backend API** · [../phase-3-backend-api/00-overview.md](../phase-3-backend-api/00-overview.md)
