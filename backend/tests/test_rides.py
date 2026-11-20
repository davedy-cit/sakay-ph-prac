"""Rides-domain tests — the weak entity, the chain, and Bagyo Mode."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.enums import GroupStatus, RideStatus, SurgeTrigger
from apps.rides.models import (
    PakyawanGroup, PassengerPreferredMode, Rating, Ride, RideLeg,
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
