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
