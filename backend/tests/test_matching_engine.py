"""MatchingEngine unit tests — geospatial + timeout logic."""

from decimal import Decimal
from uuid import uuid4

import pytest

from apps.accounts.models import Driver, Vehicle
from apps.rides.models import RideModeLookup
from apps.rides.services import (
    MatchingEngine,
    MatchStatus,
    cache_driver_location,
    get_driver_location,
    DRIVER_LOC_KEY,
)


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def tricycle_mode(db):
    return RideModeLookup.objects.create(
        mode_code="TRICYCLE",
        mode_name="Tricycle",
        base_fare=Decimal("25.00"),
        per_km_rate=Decimal("12.00"),
        seat_capacity=3,
        is_shared=False,
        booking_fee=Decimal("3.00"),
    )


@pytest.fixture
def online_driver(db, driver, tricycle_mode):
    """Driver with vehicle, online, verified, cached location near Cabuyao."""
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
    cache_driver_location(str(driver.user_id), Decimal("14.2764"), Decimal("121.1245"))
    return driver


@pytest.fixture
def offline_driver(db, tricycle_mode):
    from apps.accounts.models import User
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
    cache_driver_location(str(driver.user_id), Decimal("14.2764"), Decimal("121.1245"))
    return driver


@pytest.fixture
def faraway_driver(db, tricycle_mode):
    """Driver 50 km away — outside radius."""
    from apps.accounts.models import User
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
    cache_driver_location(str(driver.user_id), Decimal("14.5995"), Decimal("120.9842"))
    return driver


@pytest.fixture
def engine():
    return MatchingEngine()


# ── Location cache ──────────────────────────────────────────────

def test_cache_and_get_driver_location(engine, online_driver):
    loc = get_driver_location(str(online_driver.user_id))
    assert loc is not None
    lat, lng = loc
    assert lat == Decimal("14.2764")
    assert lng == Decimal("121.1245")


def test_stale_location_returns_none(engine, online_driver):
    from django.core.cache import cache
    key = DRIVER_LOC_KEY.format(driver_id=online_driver.user_id)
    cache.delete(key)
    assert get_driver_location(str(online_driver.user_id)) is None


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
    assert cand.driver_id == online_driver.user_id
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
    online_driver.vehicle.delete()
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    assert result.status == MatchStatus.NO_DRIVERS


def test_find_drivers_respects_radius(engine, online_driver, tricycle_mode):
    """Radius 0.5 km should exclude driver at 1 km."""
    # Move driver 1 km away
    cache_driver_location(str(online_driver.user_id), Decimal("14.2850"), Decimal("121.1300"))
    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
        radius_km=Decimal("0.5"),
    )
    assert result.status == MatchStatus.NO_DRIVERS


def test_find_drivers_limits_candidates(engine, tricycle_mode):
    """Only MAX_CANDIDATES returned, sorted by distance."""
    from apps.accounts.models import User
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
        cache_driver_location(str(driver.user_id), lat, lng)

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
    response = engine.handle_response(match_id, online_driver.user_id, accepted=True)

    assert response.status == MatchStatus.ACCEPTED
    assert response.driver == online_driver


def test_handle_response_decline_then_accept(engine, online_driver, tricycle_mode):
    """Two drivers: first declines, second accepts."""
    from apps.accounts.models import User
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
    cache_driver_location(str(driver2.user_id), Decimal("14.2770"), Decimal("121.1250"))

    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    match_id = result.match_id
    assert len(result.candidates) == 2

    # First driver (closest) declines
    engine.handle_response(match_id, online_driver.user_id, accepted=False)

    # Second driver accepts
    response = engine.handle_response(match_id, driver2.user_id, accepted=True)

    assert response.status == MatchStatus.ACCEPTED
    assert response.driver == driver2


def test_handle_response_all_decline_returns_no_drivers(engine, online_driver, tricycle_mode):
    from apps.accounts.models import User
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
    cache_driver_location(str(driver2.user_id), Decimal("14.2770"), Decimal("121.1250"))

    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    match_id = result.match_id

    # Both decline
    engine.handle_response(match_id, online_driver.user_id, accepted=False)
    response = engine.handle_response(match_id, driver2.user_id, accepted=False)

    assert response.status == MatchStatus.NO_DRIVERS
    assert "All drivers declined" in response.message


def test_handle_response_duplicate_ignored(engine, online_driver, tricycle_mode):
    """Duplicate response while match is still PENDING is ignored."""
    from apps.accounts.models import User
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
    cache_driver_location(str(driver2.user_id), Decimal("14.2770"), Decimal("121.1250"))

    result = engine.find_drivers(
        pickup_lat=Decimal("14.2764"),
        pickup_lng=Decimal("121.1245"),
        mode=tricycle_mode,
    )
    match_id = result.match_id
    assert len(result.candidates) == 2

    # First driver declines
    engine.handle_response(match_id, online_driver.user_id, accepted=False)
    # Second driver accepts
    engine.handle_response(match_id, driver2.user_id, accepted=True)
    # First driver tries to respond again (duplicate) - should be ignored since match is resolved
    response = engine.handle_response(match_id, online_driver.user_id, accepted=True)

    assert response.status == MatchStatus.ACCEPTED
    assert "Match already resolved" in response.message


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
        find_result.match_id, online_driver.user_id, accepted=True
    )
    assert accept_result.status == MatchStatus.ACCEPTED
    assert accept_result.driver == online_driver

    # 3. State reflects acceptance
    state = engine.get_match_state(find_result.match_id)
    assert state.status == MatchStatus.ACCEPTED
