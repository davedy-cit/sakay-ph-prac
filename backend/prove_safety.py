# Step 2.07 §3 — prove the SOS fan-out behaves.
# Step file's shell block minus the REPL `exit()`, with two repairs:
#   - get_or_create for the RIDE_MODE lookup (2.05's lesson: a bare `get`
#     assumes earlier steps seeded the row)
#   - PROTECT-aware cleanup: SOSAlert.ride is PROTECT, so the alert goes
#     before the ride — the step file's original order raised ProtectedError
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Passenger, User
from apps.core.enums import DeliveryStatus, RideMode, RideStatus, SOSStatus, UserRole
from apps.rides.models import Location, Ride, RideLeg, RideModeLookup
from apps.safety.models import SOSAlert, SOSNotification, TrustedContact

tricycle, _ = RideModeLookup.objects.get_or_create(
    mode_code=RideMode.TRICYCLE,
    defaults=dict(mode_name="Tricycle", base_fare=Decimal("25.00"),
                  per_km_rate=Decimal("12.00"), seat_capacity=3, is_shared=False),
)
a = Location.objects.create(street="A", barangay="Poblacion", city="Cabuyao",
                            province="Laguna", latitude=Decimal("14.27"), longitude=Decimal("121.12"))
b = Location.objects.create(street="B", barangay="Sala", city="Cabuyao",
                            province="Laguna", latitude=Decimal("14.25"), longitude=Decimal("121.10"))

u = User.objects.create_user(phone="09170000040", password="t", full_name="Liza Mercado",
                             user_role=UserRole.PASSENGER)
pax = Passenger.objects.create(user=u, home_address="X", gcash_number="09170000040")

ride = Ride.objects.create(passenger=pax, mode=tricycle, pickup_location=a,
                           dropoff_location=b, status=RideStatus.ONGOING)
RideLeg.objects.create(ride=ride, leg_no=1, mode=tricycle, origin_location=a,
                       dest_location=b, fare=Decimal("40.00"))
ride.recompute_chain_flags()

# ── Three trusted contacts ─────────────────────────────────────
c1 = TrustedContact.objects.create(passenger=pax, contact_name="Mama",
                                   contact_mobile="09171111111", relationship="Mother")
c2 = TrustedContact.objects.create(passenger=pax, contact_name="Ate Joy",
                                   contact_mobile="09172222222", relationship="Sister")
c3 = TrustedContact.objects.create(passenger=pax, contact_name="Barangay Hall",
                                   contact_mobile="09173333333", relationship="Barangay")

# 1. The same number twice is rejected
try:
    with transaction.atomic():
        TrustedContact.objects.create(passenger=pax, contact_name="Duplicate",
                                      contact_mobile="09171111111")
    print("*** DUPLICATE CONTACT ALLOWED ***")
except IntegrityError:
    print("duplicate contact mobile rejected: True")

# ── Raise the alert and fan out ────────────────────────────────
alert = SOSAlert.objects.create(ride=ride, raised_by=u, alert_type="harassment",
                                alert_lat=Decimal("14.261000"),
                                alert_long=Decimal("121.115000"))
for c in (c1, c2, c3):
    SOSNotification.objects.create(alert=alert, contact=c)

print("open:", alert.is_open)                                # True
print("notifications:", alert.notifications.count())          # 3
print("delivered yet:", alert.notified_count)                 # 0

# 2. The composite key on SOS_NOTIFICATION
try:
    with transaction.atomic():
        SOSNotification.objects.create(alert=alert, contact=c1)
    print("*** DUPLICATE NOTIFICATION ALLOWED ***")
except IntegrityError:
    print("duplicate (alert, contact) rejected: True")

# 3. Two contacts fail, one is delivered
alert.notifications.filter(contact__in=[c1, c2]).update(
    delivery_status=DeliveryStatus.FAILED)
alert.notifications.get(contact=c3).mark_delivered()
alert.status = SOSStatus.NOTIFIED
alert.save(update_fields=["status"])
print("delivered count:", alert.notified_count)               # 1
print("failed count:", alert.notifications.filter(
    delivery_status=DeliveryStatus.FAILED).count())           # 2

# 4. Resolution
alert.status = SOSStatus.RESOLVED
alert.resolved_at = timezone.now()
alert.save(update_fields=["status", "resolved_at"])
print("open now:", alert.is_open)                             # False
print("response_seconds:", alert.response_seconds is not None)  # True

# 5. resolved_at cannot precede triggered_at
try:
    with transaction.atomic():
        SOSAlert.objects.filter(pk=alert.pk).update(
            triggered_at=timezone.now(),
            resolved_at=timezone.now() - timezone.timedelta(hours=1))
    print("*** RESOLVED BEFORE TRIGGERED ALLOWED ***")
except IntegrityError:
    print("resolved-before-triggered rejected: True")

# 6. One SOS per ride
try:
    with transaction.atomic():
        SOSAlert.objects.create(ride=ride, raised_by=u, alert_type="second",
                                alert_lat=Decimal("14.26"), alert_long=Decimal("121.11"))
    print("*** SECOND SOS FOR ONE RIDE ALLOWED ***")
except IntegrityError:
    print("second SOS for one ride rejected: True")

# ── Clean up ───────────────────────────────────────────────────
# PROTECT-aware order: SOSAlert.ride is PROTECT — the alert (and its
# notifications, which cascade with it) goes before the ride.
alert.delete()
Ride.objects.filter(pk=ride.pk).delete()
u.delete()
Location.objects.filter(pk__in=[a.pk, b.pk]).delete()
