# Step 2.04 §3 — prove the weak entity behaves.
# Same content as the step file's shell block, minus the REPL `exit()`.
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
