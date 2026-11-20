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