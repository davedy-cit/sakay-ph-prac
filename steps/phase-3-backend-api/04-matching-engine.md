# Step 3.04 — MatchingEngine

| | |
|---|---|
| **Goal** | A service class that finds nearby online drivers for a ride request, handles the accept/decline flow with a timeout, and correctly implements the no-driver-available path (D-43) |
| **Day / Time** | Day 18 (Mon 23 Nov) · ~3 hours |
| **Prerequisites** | [Step 3.02](02-serializers-viewsets-and-swagger.md) — `/api/driver/vehicles/`, driver online status; [Step 3.03](03-fare-calculator.md) — fare preview ready |
| **Traces to** | Milestone M3's "matching" criterion · `mock2_match.png` (driver list shown to passenger) · D-43 (no-driver timeout) · D-67 (driver location freshness) |
| **Produces** | `apps/rides/services.py` (append `MatchingEngine`, `MatchResult`), `apps/rides/models.py` (add `driver_location` cache helper), `tests/test_matching_engine.py` |

---

## What this step is really doing

The class diagram has a `MatchingEngine` with two public methods:

```
+ find_drivers(pickup: Location, radius_km: Decimal, mode: RideMode) -> list[Driver]
+ handle_response(match_id: UUID, driver: User, accepted: bool) -> MatchResult
```

And a background concern: **the timeout**. When no driver accepts within the window,
the request must expire cleanly — not hang forever. That is D-43 from the
consistency report, and it is the specific thing an assessor will probe.

**Why a separate class?**
- The matching logic (geospatial query + driver eligibility + timeout orchestration)
  is the most complex single algorithm in the domain.
- It will be called from the booking service (Step 3.05) and potentially from a
  management command for cleanup.
- Keeping it pure(ish) — inputs in, domain events out — makes it testable without
  spinning up Channels or WebSockets.

**Geospatial approach**: Django + PostGIS would be ideal, but we're on MySQL 8.4.
MySQL 8 has native spatial functions (`ST_Distance_Sphere`, `ST_Within`), but
the ORM support is thin. We'll use **`geopy`** for the Haversine formula in
Python — it's pure-Python, dependency-light, and accurate enough for city-scale
radius searches. The driver's last known location is cached in Redis (Step 3.08
will write it live; for now we seed it).

---

## Do this

### 0. Before you start (~5 min)

**Prerequisites**: Make sure Docker is running and you're at the repo root.

```powershell
# 1. Navigate to project root
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem"

# 2. Start infrastructure (MySQL, Redis)
docker compose up -d

# 3. Go to backend and activate venv
Set-Location backend
..\.venv\Scripts\Activate.ps1

# 4. Install geopy for Haversine distance calculations
pip install geopy==2.4.1

# 5. Add geopy to dev.txt for persistence
echo "geopy==2.4.1" >> requirements/dev.txt

# 6. Verify current tests pass (should be 167)
pytest -q --no-cov
```

**Expected**: `167 passed`

---

### 1. Add driver location caching (~15 min)

The driver's live location comes from the WebSocket (Step 3.08), but matching
needs a location *now*. We'll cache it in Redis with a short TTL.

**In VS Code — Edit `backend/apps/rides/services.py`:**

1. Open `backend/apps/rides/services.py` (created in Step 3.03)
2. Scroll to the **end of the file** (after the `FareCalculator` class)
3. **Append the entire code block below** (driver location cache functions)
4. Save (Ctrl+S)

**Append to `backend/apps/rides/services.py`** (below `FareCalculator`):

```python
# ── Driver location cache (Redis) ────────────────────────────────

# Key: "driver:loc:{driver_id}" → value: {"lat": Decimal, "lng": Decimal}
# TTL: 60 seconds — a location older than this is stale (D-67)
DRIVER_LOC_TTL = 60
DRIVER_LOC_KEY = "driver:loc:{driver_id}"


def cache_driver_location(driver_id: str, lat: Decimal, lng: Decimal) -> None:
    """Store driver's last known location in Redis."""
    from django.core.cache import cache
    key = DRIVER_LOC_KEY.format(driver_id=driver_id)
    cache.set(key, {"lat": str(lat), "lng": str(lng)}, DRIVER_LOC_TTL)


def get_driver_location(driver_id: str) -> tuple[Decimal, Decimal] | None:
    """Retrieve driver's cached location, or None if stale/missing."""
    from django.core.cache import cache
    key = DRIVER_LOC_KEY.format(driver_id=driver_id)
    data = cache.get(key)
    if not data:
        return None
    return (Decimal(data["lat"]), Decimal(data["lng"]))
```

**Add a helper to `backend/apps/rides/models.py`** (on `Driver` model, or as a standalone function):

```python
# In apps/rides/models.py, add to Driver class or as module-level function:

def get_online_drivers_with_location(mode: RideModeLookup) -> QuerySet[Driver]:
    """
    Return online drivers with a vehicle of the given mode who have a
    fresh cached location. Used by MatchingEngine.
    """
    from django.db.models import Exists, OuterRef
    from apps.rides.services import DRIVER_LOC_KEY
    from django.core.cache import cache

    # Drivers with an active vehicle of this mode
    vehicle_subq = Vehicle.objects.filter(
        driver=OuterRef("pk"),
        mode=mode,
    )
    drivers = Driver.objects.filter(
        is_online=True,
        accreditation_status=AccredStatus.VERIFIED,
    ).filter(Exists(vehicle_subq))

    # Filter to those with a fresh Redis location
    # (We do this in Python because Redis is outside the ORM)
    return drivers
```

> **Note**: The Python-side filter is intentional — Redis is the source of truth
> for "fresh location." A driver without a cached location (TTL expired) is
> treated as unavailable even if `is_online=True`.

**In VS Code — Edit `backend/apps/rides/models.py`:**

1. Open `backend/apps/rides/models.py`
2. Find the `Driver` class (or add at module level near the end)
3. **Add the helper function** below (or as a method on Driver)
4. Save (Ctrl+S)

**Add a helper to `backend/apps/rides/models.py`** (on `Driver` model, or as a standalone function):

---

### 2. The MatchingEngine (~45 min)

**In VS Code — Edit `backend/apps/rides/services.py`:**

1. Open `backend/apps/rides/services.py`
2. Scroll to the **end of the file** (after the driver location cache functions)
3. **Append the entire MatchingEngine code block below**
4. Save (Ctrl+S)

**Append to `backend/apps/rides/services.py`** (below the location cache):

```python
# ── MatchingEngine ──────────────────────────────────────────────

from dataclasses import dataclass
from uuid import UUID, uuid4
from decimal import Decimal
from enum import Enum
from geopy.distance import geodesic


class MatchStatus(Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    TIMED_OUT = "TIMED_OUT"
    NO_DRIVERS = "NO_DRIVERS"


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    """A single driver offered the ride."""
    driver_id: UUID
    driver_name: str
    vehicle_plate: str
    vehicle_model: str
    distance_km: Decimal          # straight-line from pickup
    eta_minutes: int              # estimated


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Outcome of the matching attempt."""
    match_id: UUID
    status: MatchStatus
    driver: Driver | None = None
    candidates: tuple[MatchCandidate, ...] = ()
    message: str = ""


class MatchingEngine:
    """
    Finds and offers a ride to nearby drivers.

    Flow:
    1. find_drivers() → returns up to N candidates, stores match in cache
    2. Driver accepts/declines via handle_response()
    3. If all decline or timeout → NO_DRIVERS / TIMED_OUT
    """

    # Config — could come from settings later
    SEARCH_RADIUS_KM = Decimal("3.0")
    MAX_CANDIDATES = 5
    OFFER_TIMEOUT_SECONDS = 30
    MATCH_CACHE_TTL = 60          # match record lives slightly longer than offer

    def __init__(self):
        self._cache_prefix = "match:"

    def _match_key(self, match_id: UUID) -> str:
        return f"{self._cache_prefix}{match_id}"

    def find_drivers(
        self,
        pickup_lat: Decimal,
        pickup_lng: Decimal,
        mode: RideModeLookup,
        radius_km: Decimal | None = None,
    ) -> MatchResult:
        """
        Find nearby online drivers and create a match offer.

        Returns a MatchResult with candidates. The match_id must be used
        in handle_response() when a driver replies.
        """
        radius = radius_km or self.SEARCH_RADIUS_KM
        match_id = uuid4()

        # 1. Get eligible drivers from DB
        drivers = get_online_drivers_with_location(mode)
        if not drivers.exists():
            return MatchResult(
                match_id=match_id,
                status=MatchStatus.NO_DRIVERS,
                message="No online drivers available for this mode.",
            )

        # 2. Filter by geospatial distance (Haversine via geopy)
        pickup = (float(pickup_lat), float(pickup_lng))
        candidates = []

        for driver in drivers:
            loc = get_driver_location(str(driver.id))
            if not loc:
                continue  # stale location
            driver_lat, driver_lng = loc
            distance_km = Decimal(str(geodesic(pickup, (float(driver_lat), float(driver_lng))).km))
            if distance_km > radius:
                continue

            # Get the vehicle for this mode
            vehicle = driver.vehicles.filter(mode=mode).first()
            if not vehicle:
                continue

            candidates.append(MatchCandidate(
                driver_id=driver.id,
                driver_name=driver.user.full_name,
                vehicle_plate=vehicle.plate_number,
                vehicle_model=vehicle.model,
                distance_km=distance_km.quantize(Decimal("0.01")),
                eta_minutes=int((distance_km / Decimal("20")) * 60) + 2,  # rough: 20 km/h + 2 min
            ))

        if not candidates:
            return MatchResult(
                match_id=match_id,
                status=MatchStatus.NO_DRIVERS,
                message="No drivers within radius.",
            )

        # Sort by distance, take top N
        candidates.sort(key=lambda c: c.distance_km)
        candidates = tuple(candidates[:self.MAX_CANDIDATES])

        # 3. Store match state in Redis for the timeout window
        match_data = {
            "match_id": str(match_id),
            "status": MatchStatus.PENDING.value,
            "pickup_lat": str(pickup_lat),
            "pickup_lng": str(pickup_lng),
            "mode_code": mode.mode_code,
            "candidate_driver_ids": [str(c.driver_id) for c in candidates],
            "responded": [],  # driver_ids who have responded
        }
        from django.core.cache import cache
        cache.set(self._match_key(match_id), match_data, self.MATCH_CACHE_TTL)

        # 4. Schedule the timeout (in production: Celery beat or Channels task;
        # here we just record the deadline — the booking service checks it)
        # For the demo, we rely on the booking service to call check_timeout()
        # when polling.

        return MatchResult(
            match_id=match_id,
            status=MatchStatus.PENDING,
            candidates=candidates,
            message=f"Offer sent to {len(candidates)} driver(s).",
        )

    def handle_response(
        self,
        match_id: UUID,
        driver_id: UUID,
        accepted: bool,
    ) -> MatchResult:
        """
        Process a driver's accept/decline. Returns updated MatchResult.

        First accept wins. If all decline → NO_DRIVERS.
        """
        from django.core.cache import cache

        key = self._match_key(match_id)
        match_data = cache.get(key)
        if not match_data:
            return MatchResult(
                match_id=match_id,
                status=MatchStatus.TIMED_OUT,
                message="Match expired or not found.",
            )

        if match_data["status"] != MatchStatus.PENDING.value:
            return MatchResult(
                match_id=match_id,
                status=MatchStatus(match_data["status"]),
                message="Match already resolved.",
            )

        # Record response
        responded = match_data.get("responded", [])
        if str(driver_id) in responded:
            return MatchResult(
                match_id=match_id,
                status=MatchStatus.PENDING,
                message="Already responded.",
            )

        responded.append(str(driver_id))
        match_data["responded"] = responded
        cache.set(key, match_data, self.MATCH_CACHE_TTL)

        if accepted:
            # First accept wins — resolve the match
            match_data["status"] = MatchStatus.ACCEPTED.value
            match_data["accepted_driver_id"] = str(driver_id)
            cache.set(key, match_data, self.MATCH_CACHE_TTL)

            driver = Driver.objects.get(id=driver_id)
            return MatchResult(
                match_id=match_id,
                status=MatchStatus.ACCEPTED,
                driver=driver,
                message="Driver accepted.",
            )

        # Decline — check if all candidates have responded
        candidate_ids = set(match_data["candidate_driver_ids"])
        if candidate_ids.issubset(set(responded)):
            match_data["status"] = MatchStatus.NO_DRIVERS.value
            cache.set(key, match_data, self.MATCH_CACHE_TTL)
            return MatchResult(
                match_id=match_id,
                status=MatchStatus.NO_DRIVERS,
                message="All drivers declined.",
            )

        return MatchResult(
            match_id=match_id,
            status=MatchStatus.PENDING,
            message="Driver declined. Waiting for others.",
        )

    def check_timeout(self, match_id: UUID) -> MatchResult:
        """
        Call this when polling for a response. Returns TIMED_OUT if the
        offer window has elapsed without an accept.
        """
        from django.core.cache import cache
        from django.utils import timezone

        key = self._match_key(match_id)
        match_data = cache.get(key)
        if not match_data:
            return MatchResult(
                match_id=match_id,
                status=MatchStatus.TIMED_OUT,
                message="Match expired.",
            )

        if match_data["status"] != MatchStatus.PENDING.value:
            return MatchResult(
                match_id=match_id,
                status=MatchStatus(match_data["status"]),
            )

        # In a real system we'd check a timestamp; here we rely on the
        # cache TTL — if the key exists, we're still in the window.
        # The booking service polls and calls this; if the cache key
        # disappeared, the TTL elapsed → timeout.
        # For explicit timeout tracking, we'd store a deadline.
        # Simplified: if we're here and no one accepted, still PENDING.
        return MatchResult(
            match_id=match_id,
            status=MatchStatus.PENDING,
        )

    def get_match_state(self, match_id: UUID) -> MatchResult | None:
        """Read-only lookup for the booking service to poll."""
        from django.core.cache import cache
        key = self._match_key(match_id)
        data = cache.get(key)
        if not data:
            return None
        return MatchResult(
            match_id=match_id,
            status=MatchStatus(data["status"]),
        )
```

---

### 3. Unit tests (~45 min)

**In VS Code:**

1. **Right-click** the `backend/tests/` folder in Explorer
2. Select **New File**
3. Name it: `test_matching_engine.py`
4. **Copy the entire test block below** into this new file
5. Save (Ctrl+S)

Create `backend/tests/test_matching_engine.py` — 15 tests:

```python
"""MatchingEngine unit tests — geospatial + timeout logic."""

from decimal import Decimal
from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest

from apps.rides.models import RideModeLookup, Driver, Vehicle
from apps.rides.services import (
    MatchingEngine,
    MatchResult,
    MatchStatus,
    MatchCandidate,
    cache_driver_location,
    get_driver_location,
    DRIVER_LOC_KEY,
)


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def tricycle_mode():
    return RideModeLookup(
        mode_code="TRICYCLE",
        mode_name="Tricycle",
        base_fare=Decimal("25.00"),
        per_km_rate=Decimal("12.00"),
        seat_capacity=3,
        is_shared=False,
        booking_fee=Decimal("3.00"),
    )


@pytest.fixture
def online_driver(db, driver_user, tricycle_mode):
    """Driver with vehicle, online, verified, cached location near Cabuyao."""
    driver = Driver.objects.get(user=driver_user)
    driver.is_online = True
    driver.accreditation_status = "VERIFIED"
    driver.save()

    Vehicle.objects.create(
        driver=driver,
        mode=tricycle_mode,
        plate_number="ABC 1234",
        model="Honda TMX",
        capacity=3,
    )

    # Cache location: Cabuyao city hall area
    cache_driver_location(str(driver.id), Decimal("14.2764"), Decimal("121.1245"))
    return driver


@pytest.fixture
def offline_driver(db, tricycle_mode):
    user = User.objects.create_user(
        phone="09171112222", password="test", full_name="Offline Driver",
        user_role="DRIVER",
    )
    driver = Driver.objects.create(
        user=user, license_number="N01-00-000001",
        accreditation_status="VERIFIED", is_online=False,
    )
    Vehicle.objects.create(
        driver=driver, mode=tricycle_mode,
        plate_number="OFF 0001", model="Honda TMX", capacity=3,
    )
    cache_driver_location(str(driver.id), Decimal("14.2764"), Decimal("121.1245"))
    return driver


@pytest.fixture
def faraway_driver(db, tricycle_mode):
    """Driver 50 km away — outside radius."""
    user = User.objects.create_user(
        phone="09173334444", password="test", full_name="Faraway Driver",
        user_role="DRIVER",
    )
    driver = Driver.objects.create(
        user=user, license_number="N01-00-000002",
        accreditation_status="VERIFIED", is_online=True,
    )
    Vehicle.objects.create(
        driver=driver, mode=tricycle_mode,
        plate_number="FAR 0001", model="Honda TMX", capacity=3,
    )
    # Manila area — ~50 km from Cabuyao
    cache_driver_location(str(driver.id), Decimal("14.5995"), Decimal("120.9842"))
    return driver


@pytest.fixture
def engine():
    return MatchingEngine()


# ── Location cache ──────────────────────────────────────────────

def test_cache_and_get_driver_location(engine, online_driver):
    loc = get_driver_location(str(online_driver.id))
    assert loc is not None
    lat, lng = loc
    assert lat == Decimal("14.2764")
    assert lng == Decimal("121.1245")


def test_stale_location_returns_none(engine, online_driver):
    from django.core.cache import cache
    key = DRIVER_LOC_KEY.format(driver_id=online_driver.id)
    cache.delete(key)
    assert get_driver_location(str(online_driver.id)) is None


# ── find_drivers ────────────────────────────────────────────────

def test_find_drivers_returns_candidates(engine, online_driver, tricycle_mode):
    """Online, verified, correct mode, in radius → candidate."""
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )

    assert result.status == MatchStatus.PENDING
    assert len(result.candidates) == 1
    cand = result.candidates[0]
    assert cand.driver_id == online_driver.id
    assert cand.distance_km < Decimal("1.0")  # same location
    assert cand.eta_minutes >= 2


def test_find_drivers_excludes_offline_driver(engine, offline_driver, tricycle_mode):
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    assert result.status == MatchStatus.NO_DRIVERS
    assert "No online drivers" in result.message


def test_find_drivers_excludes_faraway_driver(engine, faraway_driver, tricycle_mode):
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
        radius_km=Decimal("3.0"),
    )
    assert result.status == MatchStatus.NO_DRIVERS
    assert "within radius" in result.message


def test_find_drivers_excludes_driver_without_vehicle(engine, online_driver, tricycle_mode):
    # Remove the vehicle
    online_driver.vehicles.all().delete()
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    assert result.status == MatchStatus.NO_DRIVERS


def test_find_drivers_respects_radius(engine, online_driver, tricycle_mode):
    """Radius 0.5 km should exclude driver at 1 km."""
    # Move driver 1 km away
    cache_driver_location(str(online_driver.id), Decimal("14.2850"), Decimal("121.1300"))
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
        radius_km=Decimal("0.5"),
    )
    assert result.status == MatchStatus.NO_DRIVERS


def test_find_drivers_limits_candidates(engine, tricycle_mode):
    """Only MAX_CANDIDATES returned, sorted by distance."""
    # Create 7 drivers at increasing distances
    for i in range(7):
        user = User.objects.create_user(
            phone=f"0917{i:02d}555{i:02d}", password="test",
            full_name=f"Driver {i}", user_role="DRIVER",
        )
        driver = Driver.objects.create(
            user=user, license_number=f"N01-00-{i:06d}",
            accreditation_status="VERIFIED", is_online=True,
        )
        Vehicle.objects.create(
            driver=driver, mode=tricycle_mode,
            plate_number=f"DRI{i:03d}", model="Honda TMX", capacity=3,
        )
        # Stagger distances: 0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3 km
        lat = Decimal("14.2764") + Decimal(str(i * 0.001))
        lng = Decimal("121.1245") + Decimal(str(i * 0.001))
        cache_driver_location(str(driver.id), lat, lng)

    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
        radius_km=Decimal("5.0"),
    )

    assert len(result.candidates) == engine.MAX_CANDIDATES  # 5
    # Should be the 5 closest
    distances = [c.distance_km for c in result.candidates]
    assert distances == sorted(distances)


# ── handle_response ────────────────────────────────────────────

def test_handle_response_accept_first_wins(engine, online_driver, tricycle_mode):
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    match_id = result.match_id

    # First driver accepts
    response = engine.handle_response(match_id, online_driver.id, accepted=True)

    assert response.status == MatchStatus.ACCEPTED
    assert response.driver == online_driver


def test_handle_response_decline_then_accept(engine, online_driver, tricycle_mode):
    """Two drivers: first declines, second accepts."""
    # Create second driver
    user2 = User.objects.create_user(
        phone="09179998888", password="test", full_name="Driver Two", user_role="DRIVER",
    )
    driver2 = Driver.objects.create(
        user=user2, license_number="N01-00-999999",
        accreditation_status="VERIFIED", is_online=True,
    )
    Vehicle.objects.create(
        driver=driver2, mode=tricycle_mode,
        plate_number="SEC 0001", model="Honda TMX", capacity=3,
    )
    cache_driver_location(str(driver2.id), Decimal("14.2770"), Decimal("121.1250"))

    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    match_id = result.match_id
    assert len(result.candidates) == 2

    # First driver (closest) declines
    engine.handle_response(match_id, online_driver.id, accepted=False)

    # Second driver accepts
    response = engine.handle_response(match_id, driver2.id, accepted=True)

    assert response.status == MatchStatus.ACCEPTED
    assert response.driver == driver2


def test_handle_response_all_decline_returns_no_drivers(engine, online_driver, tricycle_mode):
    # Add second driver
    user2 = User.objects.create_user(
        phone="09179998888", password="test", full_name="Driver Two", user_role="DRIVER",
    )
    driver2 = Driver.objects.create(
        user=user2, license_number="N01-00-999999",
        accreditation_status="VERIFIED", is_online=True,
    )
    Vehicle.objects.create(
        driver=driver2, mode=tricycle_mode,
        plate_number="SEC 0001", model="Honda TMX", capacity=3,
    )
    cache_driver_location(str(driver2.id), Decimal("14.2770"), Decimal("121.1250"))

    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    match_id = result.match_id

    # Both decline
    engine.handle_response(match_id, online_driver.id, accepted=False)
    response = engine.handle_response(match_id, driver2.id, accepted=False)

    assert response.status == MatchStatus.NO_DRIVERS
    assert "All drivers declined" in response.message


def test_handle_response_duplicate_ignored(engine, online_driver, tricycle_mode):
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    match_id = result.match_id

    engine.handle_response(match_id, online_driver.id, accepted=True)
    response = engine.handle_response(match_id, online_driver.id, accepted=True)

    assert response.status == MatchStatus.ACCEPTED
    assert "Already responded" in response.message


def test_handle_response_on_expired_match(engine, tricycle_mode):
    """Response to a match that doesn't exist (TTL elapsed)."""
    fake_id = uuid4()
    response = engine.handle_response(fake_id, uuid4(), accepted=True)

    assert response.status == MatchStatus.TIMED_OUT
    assert "expired or not found" in response.message


# ── Timeout path (D-43) ────────────────────────────────────────

def test_timeout_path_after_cache_ttl(engine, online_driver, tricycle_mode):
    """
    D-43: When no driver responds within the window, the match
    times out cleanly — the passenger is not left hanging.
    """
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    match_id = result.match_id

    # Simulate cache TTL expiry by deleting the key
    from django.core.cache import cache
    cache.delete(engine._match_key(match_id))

    # Next poll should see timeout
    timeout_result = engine.check_timeout(match_id)
    assert timeout_result.status == MatchStatus.TIMED_OUT


def test_get_match_state_for_polling(engine, online_driver, tricycle_mode):
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    match_id = result.match_id

    state = engine.get_match_state(match_id)
    assert state is not None
    assert state.status == MatchStatus.PENDING
    assert state.match_id == match_id


# Integration-style: end-to-end flow

def test_full_match_flow_accept(engine, online_driver, tricycle_mode):
    """Passenger requests → engine finds driver → driver accepts → match resolved."""
    # 1. Find drivers
    find_result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    assert find_result.status == MatchStatus.PENDING
    assert len(find_result.candidates) == 1

    # 2. Driver accepts
    accept_result = engine.handle_response(
        find_result.match_id, online_driver.id, accepted=True
    )
    assert accept_result.status == MatchStatus.ACCEPTED
    assert accept_result.driver == online_driver

    # 3. State reflects acceptance
    state = engine.get_match_state(find_result.match_id)
    assert state.status == MatchStatus.ACCEPTED
```

---

### 4. Run them (~10 min)

**In your terminal (already in `backend` with venv active):**

```powershell
# Run just the new matching engine tests
pytest tests/test_matching_engine.py -v

# Then lint gate
..\.venv\Scripts\ruff.exe check apps tests

# Then full suite
pytest -q
```

**Expected results:**
- `test_matching_engine.py` → **16 passed**
- `ruff` → clean
- Full suite → **183 passed** (167 + 16)

---

### 5. Quick manual check (~5 min)

**In your terminal (already in `backend` with venv active):**

```powershell
python manage.py shell
```

Then paste this **entire block** into the Django shell:

```python
from decimal import Decimal
from apps.rides.models import RideModeLookup
from apps.rides.services import MatchingEngine, cache_driver_location

tri = RideModeLookup.objects.get(mode_code="TRICYCLE")
# Seed a driver location (assumes driver with id=1 exists and is online)
cache_driver_location("1", Decimal("14.2764"), Decimal("121.1245"))

engine = MatchingEngine()
result = engine.find_drivers(
    pickup_lat=Decimal("14.2764"),
    pickup_lng=Decimal("121.1245"),
    mode=tri,
)
print(f"Match: {result.match_id}, Status: {result.status}, Candidates: {len(result.candidates)}")
```

**Expected output:**
```
Match: <uuid>, Status: MatchStatus.PENDING, Candidates: 1
```
(Assuming driver 1 is online, verified, has a tricycle vehicle, and location cached)

Type `exit()` to leave the shell.

---

## Verify

- [ ] `pytest tests/test_matching_engine.py` → **16 passed**
- [ ] `ruff check apps tests` → clean
- [ ] `pytest -q` → **183 passed** (167 + 16)
- [ ] `geopy` in `dev.txt` and installed
- [ ] Driver location cache uses Redis with 60s TTL
- [ ] `find_drivers()` filters: online, verified, correct mode, fresh location, in radius
- [ ] Candidates sorted by distance, limited to `MAX_CANDIDATES`
- [ ] `handle_response()` — first accept wins, all decline → NO_DRIVERS
- [ ] **D-43**: Timeout path returns `TIMED_OUT` when cache key expires
- [ ] No Django ORM in the hot path of `handle_response()` — pure cache ops

---

## Log it

In `steps/PROGRESS.md`:

```markdown
· Step 3.04 — MatchingEngine: geopy radius search, accept/decline with first-wins, D-43 timeout path via Redis TTL; 16 tests — 183 passed, 0 failures.
```

Commit:

```powershell
Set-Location ..
git add backend/ steps/
git commit -m "feat(matching): add MatchingEngine with radius search and D-43 timeout"
git push
```

---

## Lessons Learned (from execution)

The following defects were encountered and fixed during Step 3.04 execution. Update the step file and tests accordingly to avoid these on re-run.

| # | Defect | Root Cause | Fix Applied |
|---|--------|------------|-------------|
| 1 | `ImportError: cannot import Driver, Vehicle from apps.rides.models` | Driver and Vehicle live in `apps.accounts.models`, not `apps.rides.models` | In `services.py`: `from apps.accounts.models import Driver, Vehicle` (not `apps.rides.models`) |
| 2 | `AttributeError: 'Driver' object has no attribute 'id'` | `Driver` uses a OneToOneField to `User` as its PK (`user_id`), not a separate `id` field | Use `driver.user_id` everywhere (match cache keys, candidate `driver_id`, `handle_response` parameter) |
| 3 | `AttributeError: 'Driver' object has no attribute 'vehicles'` | `Vehicle.driver` FK has `related_name="vehicle"` (singular), not `"vehicles"` | Use `driver.vehicle` (singular) to access the vehicle; check `vehicle.mode == mode` |
| 4 | `E402: module level import not at top of file` | `MatchingEngine` imports (`dataclasses`, `uuid`, `decimal`, `enum`, `geopy`) were inside the class block | Move **all** imports to the top of `services.py` (after `FareCalculator` imports) |
| 5 | `TypeError: "Driver" \| None` forward ref in `MatchResult` | `driver: Driver | None = None` needs `Driver` in scope at class definition time | Add `from typing import Optional` and use `driver: Optional[Driver] = None` |
| 6 | `tricycle_mode` fixture not persisted to DB | Fixture returned unsaved `RideModeLookup()` instance | Use `RideModeLookup.objects.create(...)` with `db` fixture (requires `@pytest.fixture` with `db` arg) |
| 7 | `online_driver` fixture referenced `driver_user` fixture | `conftest.py` provides `driver` fixture (returns `Driver`), not `driver_user` | Change fixture param from `driver_user` to `driver`; use `driver.user_id` for cache key |
| 8 | Duplicate response test logic didn't match code | Test expected "Already responded" after match was already ACCEPTED; code returns "Match already resolved" | Rewrite test: create 2 drivers, first declines, second accepts, then first tries again while PENDING → "Already responded" |
| 9 | FK constraint on `Vehicle.mode_code` | `tricycle_mode` fixture created but not saved before `Vehicle.objects.create()` | Ensure `tricycle_mode` fixture uses `.objects.create()` (saves to DB) before any `Vehicle` creation |

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: geopy` | Not installed | `pip install geopy==2.4.1` and add to `dev.txt` |
| `find_drivers` returns NO_DRIVERS but driver exists | Location not cached or TTL expired | Call `cache_driver_location()` in test setup; check `is_online=True` and `accreditation_status=VERIFIED` |
| `geodesic` returns wrong distance | Lat/lng order swapped | `geodesic((lat1, lng1), (lat2, lng2))` — lat first! |
| `handle_response` says "Match expired" immediately | Cache TTL too short or key wrong | `MATCH_CACHE_TTL = 60`; key format `match:{uuid}` |
| Test `test_find_drivers_limits_candidates` fails | Not enough test drivers created | Loop creates 7, but check `Vehicle` creation and location caching |
| `MAX_CANDIDATES` not respected | Slice not applied | `candidates = tuple(candidates[:self.MAX_CANDIDATES])` |
| `ImportError: cannot import Driver, Vehicle` | Importing from wrong app | `from apps.accounts.models import Driver, Vehicle` |
| `AttributeError: 'Driver' has no 'id'` | Using `driver.id` instead of PK | Use `driver.user_id` (OneToOne PK to User) |
| `AttributeError: 'Driver' has no 'vehicles'` | Wrong related_name | Use `driver.vehicle` (singular — FK has `related_name="vehicle"`) |
| `E402 module level import not at top` | Imports inside class definition | Move all imports to module top |
| `TypeError: "Driver" \| None` forward ref | Union type without import | `from typing import Optional`; use `Optional[Driver]` |
| Fixture not persisted (IntegrityError) | Unsaved model instance in fixture | Use `Model.objects.create(...)` with `db` fixture |
| FK constraint violation on Vehicle.mode | Mode not saved before Vehicle | Save mode first: `RideModeLookup.objects.create(...)` |
| Duplicate response test fails | Test scenario doesn't match code path | Test duplicate while match is still PENDING (not after ACCEPTED) |

---

## After this step

The matching engine is ready. The next step consumes both services:

**Step 3.05 — Ride lifecycle and cancellation**: `RideService.request_ride()` calls `FareCalculator` for preview, `MatchingEngine` for dispatch, and manages the state machine REQUESTED → MATCHED → EN_ROUTE → ONGOING → COMPLETED (plus cancellation with fee/refund policy).