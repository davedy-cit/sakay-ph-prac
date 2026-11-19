# Step 2.05 §3 — prove the six feature models behave.
# Same content as the step file's shell block, minus the REPL `exit()`.
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
# get_or_create, not get: RIDE_MODE only carries what earlier steps seeded,
# and the §6 duplicate test needs TWO DISTINCT modes — a `car == tricycle`
# fallback would violate uq_prefmode_passenger_mode outside any try-block.
tricycle, _ = RideModeLookup.objects.get_or_create(
    mode_code=RideMode.TRICYCLE,
    defaults=dict(mode_name="Tricycle", base_fare=Decimal("25.00"),
                  per_km_rate=Decimal("12.00"), seat_capacity=3, is_shared=False),
)
car, _ = RideModeLookup.objects.get_or_create(
    mode_code=RideMode.CAR,
    defaults=dict(mode_name="Car", base_fare=Decimal("50.00"),
                  per_km_rate=Decimal("18.00"), seat_capacity=4, is_shared=False),
)

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
