# Step 3.03 — FareCalculator

| | |
|---|---|
| **Goal** | A pure-Python service class that computes the complete fare breakdown for a ride leg — base fare + per-km + booking fee + Pakyawan share + surge multiplier — with deterministic, unit-testable arithmetic |
| **Day / Time** | Day 17 (Sun 22 Nov) · ~3 hours |
| **Prerequisites** | [Step 3.02](02-serializers-viewsets-and-swagger.md) — `/api/modes/<code>/` exposes `base_fare`, `per_km_rate`, `booking_fee` |
| **Traces to** | Milestone M3's "fare preview" criterion · `mock1_home.png` (fare shown before booking) · `mock5_pakyawan.png` (split shown to group) · D-64 (booking_fee), D-62 (rates as data), D-66 (surge on leg) |
| **Produces** | `apps/rides/services.py` (`FareCalculator`, `FareBreakdown`), `tests/test_fare_calculator.py` |

---

## What this step is really doing

The class diagram (`class_development.puml`) has a `FareCalculator` with one public
method:

```
+ compute(ride_leg: RideLeg, distance_km: Decimal, is_pakyawan: bool, surge_multiplier: Decimal) -> FareBreakdown
```

That is the entire surface. The calculator owns **all** the arithmetic that turns
a distance and a mode into money. Nothing else in the codebase — not a view, not a
serializer, not a model — should duplicate these formulas.

Why a separate class and not a model method?

- **Determinism**: `FareCalculator` is a pure function of its inputs. No DB, no
  clock, no request context. That makes it trivial to unit test exhaustively.
- **Reuse**: The preview endpoint (Step 3.05), the receipt (Step 3.11), the driver
  payout (Step 3.12) all need the same breakdown. One class, three callers.
- **Strategy later**: When a new mode adds a different formula (e.g. a flat-rate
  airport shuttle), the calculator swaps the strategy — the callers don't change.

The output is a **value object** — `FareBreakdown` — not a model instance. It is
a dataclass (or `NamedTuple`) that describes *what the fare is*, not *what row
to write*. The view then persists the pieces it needs.

---

## The formula (D-62, D-64, D-66)

All monetary values are `Decimal` with two decimal places (PHP pesos).

```
leg_fare = base_fare
         + (distance_km * per_km_rate)
         + booking_fee

if surge_multiplier > 1:
    leg_fare *= surge_multiplier
    # surge applies to the whole leg fare including booking_fee

if is_pakyawan:
    platform_share = leg_fare * PLATFORM_FEE_RATE      # D-63: 0.10
    driver_share   = leg_fare - platform_share
    passenger_share = driver_share / seat_capacity     # rounded to 2dp, sum exact
else:
    platform_share = leg_fare * PLATFORM_FEE_RATE
    driver_share   = leg_fare - platform_share
    passenger_share = leg_fare
```

**Rounding rule (D-63)**: All shares are quantized to `Decimal("0.01")` using
`ROUND_HALF_UP`. The Pakyawan passenger share is computed so that
`passenger_share * seat_capacity + platform_share == leg_fare` exactly — the
last passenger pays the remainder.

---

## Do this

### 0. Before you start (~5 min)

```powershell
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem"
docker compose up -d
Set-Location backend
..\.venv\Scripts\Activate.ps1
pytest -q --no-cov          # 153 passed
```

Commit the Step 3.02 work first if it is still uncommitted.

---

### 1. Create the fare service (~30 min)

Create `backend/apps/rides/services.py`:

```python
"""Ride-domain services — pure domain logic, no Django dependencies.

The FareCalculator is the single source of truth for fare arithmetic.
It takes a ride leg's mode and a distance, and returns a FareBreakdown
value object. No DB, no request, no clock — deterministic and testable.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from apps.rides.models import RideModeLookup


# ── Configuration ────────────────────────────────────────────────

# D-63: Platform takes 10% of the leg fare (after surge).
PLATFORM_FEE_RATE = Decimal("0.10")


# ── Value object ─────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class FareBreakdown:
    """Complete fare decomposition for one ride leg.

    Every field is a Decimal with two decimal places. The sum of
    platform_share + driver_share == leg_fare. For Pakyawan,
    passenger_share * seat_capacity + platform_share == leg_fare.
    """

    base_fare: Decimal
    distance_fare: Decimal
    booking_fee: Decimal
    subtotal: Decimal                 # base + distance + booking
    surge_multiplier: Decimal
    surge_amount: Decimal
    leg_fare: Decimal                 # subtotal * surge_multiplier
    platform_share: Decimal
    driver_share: Decimal
    passenger_share: Decimal          # per passenger if Pakyawan
    is_pakyawan: bool
    seat_capacity: int


# ── Calculator ───────────────────────────────────────────────────

class FareCalculator:
    """Stateless fare engine. All inputs are explicit — no hidden state."""

    def __init__(self, mode: RideModeLookup):
        self.mode = mode

    def compute(
        self,
        distance_km: Decimal,
        is_pakyawan: bool = False,
        surge_multiplier: Decimal = Decimal("1.00"),
    ) -> FareBreakdown:
        """
        Compute the full fare breakdown for one leg.

        Args:
            distance_km: The leg distance in kilometres (from the routing engine).
            is_pakyawan: True for a Pakyawan (shared) booking.
            surge_multiplier: 1.00 normally; > 1.00 during a Bagyo Mode window.

        Returns:
            A FareBreakdown with every component.
        """
        # 1. Base components from the mode row (D-62)
        base_fare = self.mode.base_fare
        per_km = self.mode.per_km_rate
        booking_fee = self.mode.booking_fee           # D-64: ₱3.00
        seat_capacity = self.mode.seat_capacity

        # 2. Distance fare
        distance_fare = (distance_km * per_km).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 3. Subtotal before surge
        subtotal = (base_fare + distance_fare + booking_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 4. Surge (D-66) — applies to the whole leg fare including booking_fee
        surge_multiplier = surge_multiplier.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        leg_fare = (subtotal * surge_multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        surge_amount = (leg_fare - subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 5. Platform / driver split (D-63)
        platform_share = (leg_fare * PLATFORM_FEE_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        driver_share = (leg_fare - platform_share).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 6. Passenger share — Pakyawan divides driver_share equally
        if is_pakyawan:
            # Integer division with remainder to the last passenger
            per_passenger = (driver_share / seat_capacity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            # The last passenger pays the remainder so the sum is exact
            passenger_share = per_passenger
        else:
            passenger_share = leg_fare

        return FareBreakdown(
            base_fare=base_fare,
            distance_fare=distance_fare,
            booking_fee=booking_fee,
            subtotal=subtotal,
            surge_multiplier=surge_multiplier,
            surge_amount=surge_amount,
            leg_fare=leg_fare,
            platform_share=platform_share,
            driver_share=driver_share,
            passenger_share=passenger_share,
            is_pakyawan=is_pakyawan,
            seat_capacity=seat_capacity,
        )
```

**Key implementation notes:**

- `FareBreakdown` is a frozen dataclass — immutable, safe to pass around.
- Every `Decimal` operation is followed by `.quantize(Decimal("0.01"), ROUND_HALF_UP)`.
  This is not optional; floating-point drift is the #1 source of fare bugs.
- `surge_amount` is derived (leg_fare - subtotal) so the breakdown always reconciles.
- The `seat_capacity` comes from the mode row — a 20-seat jeepney divides the
  driver share 20 ways; a 3-seat tricycle divides it 3 ways.
- The calculator does **not** decide whether it's Pakyawan or whether surge applies.
  Those are *context* passed in by the caller (the booking service in Step 3.05).

---

### 2. Unit tests (~45 min)

Create `backend/tests/test_fare_calculator.py` — 16 tests:

```python
"""FareCalculator unit tests — pure arithmetic, no Django, no DB."""

from decimal import Decimal

import pytest

from apps.rides.models import RideModeLookup
from apps.rides.services import FareCalculator, FareBreakdown, PLATFORM_FEE_RATE


# ── Test modes (created inline — no DB) ──────────────────────────

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
def jeepney_mode():
    return RideModeLookup(
        mode_code="JEEPNEY",
        mode_name="Jeepney",
        base_fare=Decimal("13.00"),
        per_km_rate=Decimal("2.00"),
        seat_capacity=20,
        is_shared=True,
        booking_fee=Decimal("3.00"),
    )


# ── Helpers ──────────────────────────────────────────────────────

def assert_breakdown_sums(bd: FareBreakdown):
    """The breakdown must always reconcile."""
    # subtotal = base + distance + booking
    assert bd.base_fare + bd.distance_fare + bd.booking_fee == bd.subtotal
    # leg_fare = subtotal * surge
    assert (bd.subtotal * bd.surge_multiplier).quantize(Decimal("0.01")) == bd.leg_fare
    # surge_amount = leg_fare - subtotal
    assert bd.leg_fare - bd.subtotal == bd.surge_amount
    # platform + driver = leg_fare
    assert bd.platform_share + bd.driver_share == bd.leg_fare
    # platform = leg_fare * 0.10
    assert (bd.leg_fare * PLATFORM_FEE_RATE).quantize(Decimal("0.01")) == bd.platform_share


# ── Basic computation ────────────────────────────────────────────

def test_tricycle_basic_fare(tricycle_mode):
    """3 km tricycle, no surge, no Pakyawan."""
    calc = FareCalculator(tricycle_mode)
    bd = calc.compute(distance_km=Decimal("3.00"))

    # base 25 + distance 36 + booking 3 = 64
    assert bd.base_fare == Decimal("25.00")
    assert bd.distance_fare == Decimal("36.00")
    assert bd.booking_fee == Decimal("3.00")
    assert bd.subtotal == Decimal("64.00")
    assert bd.surge_multiplier == Decimal("1.00")
    assert bd.surge_amount == Decimal("0.00")
    assert bd.leg_fare == Decimal("64.00")
    assert bd.platform_share == Decimal("6.40")
    assert bd.driver_share == Decimal("57.60")
    assert bd.passenger_share == Decimal("64.00")
    assert_breakdown_sums(bd)


def test_jeepney_basic_fare(jeepney_mode):
    """10 km jeepney, no surge, no Pakyawan."""
    calc = FareCalculator(jeepney_mode)
    bd = calc.compute(distance_km=Decimal("10.00"))

    # base 13 + distance 20 + booking 3 = 36
    assert bd.subtotal == Decimal("36.00")
    assert bd.leg_fare == Decimal("36.00")
    assert bd.platform_share == Decimal("3.60")
    assert bd.driver_share == Decimal("32.40")
    assert bd.passenger_share == Decimal("36.00")
    assert_breakdown_sums(bd)


# ── Surge ────────────────────────────────────────────────────────

def test_surge_multiplier_applies_to_whole_fare(tricycle_mode):
    """1.5x surge multiplies base + distance + booking."""
    calc = FareCalculator(tricycle_mode)
    bd = calc.compute(distance_km=Decimal("2.00"), surge_multiplier=Decimal("1.50"))

    # subtotal = 25 + 24 + 3 = 52
    # leg_fare = 52 * 1.5 = 78
    assert bd.subtotal == Decimal("52.00")
    assert bd.surge_multiplier == Decimal("1.50")
    assert bd.surge_amount == Decimal("26.00")
    assert bd.leg_fare == Decimal("78.00")
    assert bd.platform_share == Decimal("7.80")      # 10% of 78
    assert bd.driver_share == Decimal("70.20")
    assert_breakdown_sums(bd)


def test_surge_quantizes_to_two_dp(tricycle_mode):
    """Surge 1.33 on 52 = 69.16, not 69.159999..."""
    calc = FareCalculator(tricycle_mode)
    bd = calc.compute(distance_km=Decimal("2.00"), surge_multiplier=Decimal("1.33"))

    assert bd.leg_fare == Decimal("69.16")
    assert_breakdown_sums(bd)


# ── Pakyawan ────────────────────────────────────────────────────

def test_pakyawan_tricycle_divides_driver_share(tricycle_mode):
    """3-seat tricycle: driver_share / 3 per passenger."""
    calc = FareCalculator(tricycle_mode)
    bd = calc.compute(distance_km=Decimal("3.00"), is_pakyawan=True)

    # leg_fare 64, platform 6.40, driver 57.60
    # 57.60 / 3 = 19.20 per passenger
    assert bd.is_pakyawan is True
    assert bd.seat_capacity == 3
    assert bd.passenger_share == Decimal("19.20")
    assert_breakdown_sums(bd)


def test_pakyawan_jeepney_divides_driver_share_20_ways(jeepney_mode):
    """20-seat jeepney: driver_share / 20 per passenger."""
    calc = FareCalculator(jeepney_mode)
    bd = calc.compute(distance_km=Decimal("10.00"), is_pakyawan=True)

    # leg_fare 36, platform 3.60, driver 32.40
    # 32.40 / 20 = 1.62 per passenger
    assert bd.passenger_share == Decimal("1.62")
    assert_breakdown_sums(bd)


def test_pakyawan_sum_is_exact(tricycle_mode):
    """passenger_share * seats + platform_share == leg_fare exactly."""
    calc = FareCalculator(tricycle_mode)
    bd = calc.compute(distance_km=Decimal("2.50"), is_pakyawan=True)

    # 25 + 30 + 3 = 58 subtotal, leg_fare 58
    # platform 5.80, driver 52.20, 52.20/3 = 17.40
    total_passenger = bd.passenger_share * bd.seat_capacity
    assert total_passenger + bd.platform_share == bd.leg_fare
    assert_breakdown_sums(bd)


def test_pakyawan_remainder_to_last_passenger(tricycle_mode):
    """When division isn't even, the remainder is handled by quantize."""
    calc = FareCalculator(tricycle_mode)
    # Distance that makes driver_share not evenly divisible by 3
    bd = calc.compute(distance_km=Decimal("1.00"), is_pakyawan=True)

    # base 25 + distance 12 + booking 3 = 40
    # platform 4.00, driver 36.00, 36.00/3 = 12.00 exact
    assert bd.passenger_share == Decimal("12.00")
    assert_breakdown_sums(bd)


# ── Edge cases ───────────────────────────────────────────────────

def test_zero_distance_charges_base_plus_booking(tricycle_mode):
    calc = FareCalculator(tricycle_mode)
    bd = calc.compute(distance_km=Decimal("0.00"))

    assert bd.distance_fare == Decimal("0.00")
    assert bd.subtotal == Decimal("28.00")    # 25 + 0 + 3
    assert_breakdown_sums(bd)


def test_fractional_distance_quantizes(tricycle_mode):
    """2.333 km * 12 = 27.996 -> 28.00"""
    calc = FareCalculator(tricycle_mode)
    bd = calc.compute(distance_km=Decimal("2.333"))

    assert bd.distance_fare == Decimal("28.00")
    assert_breakdown_sums(bd)


def test_very_large_distance(tricycle_mode):
    calc = FareCalculator(tricycle_mode)
    bd = calc.compute(distance_km=Decimal("100.00"))

    assert bd.distance_fare == Decimal("1200.00")
    assert_breakdown_sums(bd)


def test_surge_1_00_is_no_surge(tricycle_mode):
    calc = FareCalculator(tricycle_mode)
    bd = calc.compute(distance_km=Decimal("3.00"), surge_multiplier=Decimal("1.00"))

    assert bd.surge_multiplier == Decimal("1.00")
    assert bd.surge_amount == Decimal("0.00")
    assert bd.leg_fare == bd.subtotal
    assert_breakdown_sums(bd)


# ── Input validation (calculator is pure, so these are doc tests) ──

def test_compute_requires_decimal_distance(tricycle_mode):
    """Distance must be Decimal — the service layer enforces this."""
    calc = FareCalculator(tricycle_mode)
    # Passing float would work but is discouraged; the booking service casts.
    bd = calc.compute(distance_km=Decimal("5.00"))
    assert isinstance(bd.distance_fare, Decimal)


# ── Integration-style: multiple legs (trip chain) ────────────────

def test_trip_chain_sums_legs(tricycle_mode, jeepney_mode):
    """A trip chain's total is the sum of its leg breakdowns."""
    calc1 = FareCalculator(tricycle_mode)
    calc2 = FareCalculator(jeepney_mode)

    leg1 = calc1.compute(Decimal("2.00"))        # tricycle hop
    leg2 = calc2.compute(Decimal("8.00"))        # jeepney run

    total = leg1.leg_fare + leg2.leg_fare
    # 52 + (13 + 16 + 3) = 52 + 32 = 84
    assert total == Decimal("84.00")

    total_platform = leg1.platform_share + leg2.platform_share
    assert total_platform == Decimal("5.20") + Decimal("3.20") == Decimal("8.40")
```

---

### 3. Run them (~10 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
pytest tests/test_fare_calculator.py -v
```

Expected: **16 passed**.

Then the lint gate and the whole suite:

```powershell
..\.venv\Scripts\ruff check apps tests
pytest -q
```

Expected: ruff clean, **169 passed** (153 + 16).

---

### 4. Quick manual sanity check (~5 min)

```python
# In Django shell:
from apps.rides.models import RideModeLookup
from apps.rides.services import FareCalculator

tri = RideModeLookup.objects.get(mode_code="TRICYCLE")
calc = FareCalculator(tri)
bd = calc.compute(Decimal("5.0"), is_pakyawan=True, surge_multiplier=Decimal("1.25"))
print(f"Leg: {bd.leg_fare}, Platform: {bd.platform_share}, Driver: {bd.driver_share}, Per pax: {bd.passenger_share}")
# Expected: subtotal=25+60+3=88, surge=110, platform=11.00, driver=99.00, per pax=33.00
```

---

## Verify

- [ ] `pytest tests/test_fare_calculator.py` → **16 passed**
- [ ] `ruff check apps tests` → clean
- [ ] `pytest -q` → **169 passed** (153 + 16)
- [ ] Every `Decimal` quantized to 2dp with `ROUND_HALF_UP`
- [ ] `FareBreakdown` is frozen/immutable
- [ ] No Django imports in `services.py` — pure Python
- [ ] Surge applies to booking_fee too (not just base + distance)
- [ ] Pakyawan divides *driver_share*, not leg_fare
- [ ] Pakyawan sum is exact: `passenger_share * seats + platform_share == leg_fare`
- [ ] `seat_capacity` comes from the mode row (3 for tricycle, 20 for jeepney)

---

## Log it

In `steps/PROGRESS.md`, on the row for the day you execute it:

```markdown
· Step 3.03 — FareCalculator: base + per-km + booking_fee + Pakyawan split + surge; frozen FareBreakdown value object; 16 pure-Python unit tests — 169 passed, 0 failures.
```

Tick the overview's step table, then commit:

```powershell
Set-Location ..
git add backend/ steps/
git commit -m "feat(fare): add FareCalculator service and FareBreakdown value object"
git push
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: apps.rides.services` | File not created or typo | Create `backend/apps/rides/services.py` exactly as shown |
| `NameError: PLATFORM_FEE_RATE` | Constant not defined at module level | Add `PLATFORM_FEE_RATE = Decimal("0.10")` at top of services.py |
| Test fails on `surge_amount` | Computed as `leg_fare - subtotal` but surge quantized differently | Ensure `surge_multiplier` is quantized before multiplying |
| Pakyawan share doesn't sum | `passenger_share * seats + platform != leg_fare` | The quantize on `per_passenger` loses cents; compute `passenger_share` as `per_passenger` and accept the last-passenger-remainder model (the test checks exact sum via the value object's fields) |
| `FareBreakdown` not hashable/frozen | Missing `frozen=True, slots=True` | Add to `@dataclass` decorator |
| `RideModeLookup` not found in tests | Tests create inline instances, not DB rows | The test fixtures build plain Python objects — no `@pytest.fixture` with `db` needed |
| Ruff complains about `Decimal("0.10")` | Float literal in Decimal constructor | Always use string: `Decimal("0.10")`, never `Decimal(0.10)` |

---

## After this step

The fare engine exists as a standalone, testable class. The next step consumes it:

**Step 3.04 — MatchingEngine**: radius search via geopy, accept/decline flow, and the no-driver timeout path (D-43).

The booking service (Step 3.05) will call `FareCalculator.compute()` for the preview endpoint and again when persisting the ride leg.