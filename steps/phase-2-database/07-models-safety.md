# Step 2.07 — Models: Safety

| | |
|---|---|
| **Goal** | SOS_ALERT, TRUSTED_CONTACT and SOS_NOTIFICATION exist; an alert can fan out to every trusted contact with per-contact delivery state |
| **Day / Time** | Day 13 (Wed 18 Nov) · ~1 hour |
| **Prerequisites** | [Step 2.06](06-models-payments.md) |
| **Produces** | `backend/apps/safety/models.py` |

---

## The smallest app, and the one with the most interesting shape

Three tables, and the middle one is the third associative entity in your schema.
`SOS_NOTIFICATION` resolves the M:N between `SOS_ALERT` and `TRUSTED_CONTACT` — one
alert notifies many contacts, and one contact can be notified by many alerts. The
relationship carries its own attribute, `delivery_status`, which is exactly what
makes it an associative entity rather than a plain join table.

**One design limitation to notice and record.** `SOS_ALERT.ride_id` is NOT NULL and
UNIQUE, which means **an SOS can only be raised during a ride.** A passenger walking
to a pickup point, or a driver between trips, has no way to trigger one. That is what
the schema says, and it is a reasonable scope decision for a capstone — but it is a
real limitation, and `docs/plan/design-freeze.md` is where limitations get listed.
Add it there.

---

## Do this

### 1. Write the models (~40 min)

Create `backend/apps/safety/models.py`:

```python
# backend/apps/safety/models.py
"""Safety-domain models: tables 20-22 in database/schema_listing.md.

SOS Bantay. Notification delivery is simulated — no SMS gateway is
integrated — but the fan-out, the per-contact state and the resolution
lifecycle are real and are what the feature demonstrates.
"""

import uuid

from django.db import models
from django.utils import timezone

from apps.core.enums import DeliveryStatus, SOSStatus


class TrustedContact(models.Model):
    """Someone to notify when a passenger raises an SOS. Table 21.

    Resolves ``SOSAlert.notifiedContacts``, which the class diagram carried
    as a multivalued attribute. A passenger has 0..* of these.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    passenger = models.ForeignKey(
        "accounts.Passenger",
        on_delete=models.CASCADE,
        related_name="trusted_contacts",
        db_column="passenger_id",
    )
    contact_name = models.CharField(max_length=120)
    contact_mobile = models.CharField(max_length=15)
    relationship = models.CharField(max_length=30, blank=True)

    class Meta:
        db_table = "TRUSTED_CONTACT"
        verbose_name = "trusted contact"
        verbose_name_plural = "trusted contacts"
        ordering = ["passenger", "contact_name"]
        constraints = [
            # The same number twice is a mistake, not a preference.
            models.UniqueConstraint(
                fields=["passenger", "contact_mobile"],
                name="uq_contact_passenger_mobile",
            ),
        ]

    def __str__(self) -> str:
        label = f" ({self.relationship})" if self.relationship else ""
        return f"{self.contact_name}{label} — {self.contact_mobile}"


class SOSAlert(models.Model):
    """An emergency alert raised during a ride. Table 20.

    ``ride`` is NOT NULL + UNIQUE: at most one SOS per ride (1 : 0..1). That
    also means an SOS can only be raised *during* a ride — a limitation worth
    recording, not a bug.

    ``raised_by`` points at USER rather than PASSENGER because either party
    can raise one; the schema says so and the use-case diagram agrees.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ride = models.OneToOneField(
        "rides.Ride", on_delete=models.PROTECT, related_name="sos_alert", db_column="ride_id"
    )
    raised_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="sos_alerts_raised",
        db_column="raised_by",
    )
    alert_type = models.CharField(
        max_length=20,
        help_text="Free text, e.g. 'accident', 'harassment', 'breakdown'.",
    )
    # Snapshotted at trigger time, not read from TRIP_TRACKING: the position
    # at the moment of the alert is evidence and must not move afterwards.
    alert_lat = models.DecimalField(max_digits=9, decimal_places=6)
    alert_long = models.DecimalField(max_digits=9, decimal_places=6)

    status = models.CharField(
        max_length=12, choices=SOSStatus.choices, default=SOSStatus.TRIGGERED
    )
    triggered_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "SOS_ALERT"
        verbose_name = "SOS alert"
        verbose_name_plural = "SOS alerts"
        ordering = ["-triggered_at"]
        indexes = [
            models.Index(fields=["status", "-triggered_at"], name="idx_sos_open"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(resolved_at__isnull=True)
                | models.Q(resolved_at__gte=models.F("triggered_at")),
                name="ck_sos_resolved_after_trigger",
            ),
        ]

    def __str__(self) -> str:
        return f"SOS {self.alert_type} ({self.status}) — {self.triggered_at:%d %b %H:%M}"

    @property
    def is_open(self) -> bool:
        """True while the alert still needs attention."""
        return self.status in {
            SOSStatus.TRIGGERED,
            SOSStatus.NOTIFIED,
            SOSStatus.RESPONDING,
        }

    @property
    def response_seconds(self):
        """Time to resolution, or None while still open."""
        if not self.resolved_at:
            return None
        return int((self.resolved_at - self.triggered_at).total_seconds())

    @property
    def notified_count(self) -> int:
        """How many contacts were actually reached."""
        return self.notifications.filter(
            delivery_status=DeliveryStatus.DELIVERED
        ).count()

    @property
    def coordinates(self) -> tuple[float, float]:
        """(lat, lon) as floats, ready for Leaflet."""
        return float(self.alert_lat), float(self.alert_long)


class SOSNotification(models.Model):
    """Associative entity: SOS_ALERT × TRUSTED_CONTACT. Table 22.

    Resolves the M:N — one alert notifies many contacts, one contact can be
    notified by many alerts. ``delivery_status`` is the attribute that makes
    this an associative entity rather than a plain join table.

    The documented key is ``(alert_id, contact_id)``; as with the other three
    associative entities, uniqueness comes from a UniqueConstraint because
    Django has no composite primary key.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    alert = models.ForeignKey(
        SOSAlert,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_column="alert_id",
    )
    contact = models.ForeignKey(
        TrustedContact,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_column="contact_id",
    )
    notified_at = models.DateTimeField(default=timezone.now)
    delivery_status = models.CharField(
        max_length=12, choices=DeliveryStatus.choices, default=DeliveryStatus.SENT
    )

    class Meta:
        db_table = "SOS_NOTIFICATION"
        verbose_name = "SOS notification"
        verbose_name_plural = "SOS notifications"
        ordering = ["alert", "contact"]
        constraints = [
            models.UniqueConstraint(
                fields=["alert", "contact"], name="uq_sosnotif_alert_contact"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.contact.contact_name}: {self.delivery_status}"

    def mark_delivered(self, save: bool = True) -> None:
        """Record a successful (simulated) delivery."""
        self.delivery_status = DeliveryStatus.DELIVERED
        self.notified_at = timezone.now()
        if save:
            super().save(update_fields=["delivery_status", "notified_at"])
```

**Three points worth understanding.**

**`alert_lat` / `alert_long` are a snapshot, not a reference.** It would be tempting
to read the position from `TRIP_TRACKING` when displaying the alert. Do not: the
whole point of an SOS record is that it captures where the passenger *was* when they
raised it. A ping table is a moving target.

**`on_delete=CASCADE` on both sides of `SOSNotification`.** This is the one place in
the project where cascade is right for a contact: if a passenger deletes a trusted
contact, the record that this contact was notified about an old alert is not worth
keeping. Contrast `SOSAlert.ride` with `PROTECT` — an alert is evidence and must
survive.

**`raise_by` points at `User`, not `Passenger`.** Both a passenger and a driver can
trigger an SOS, which is why the schema uses `USER.user_id` here.

### 2. Migrate (~10 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
python manage.py makemigrations safety
python manage.py migrate
```

### 3. Prove the fan-out (~20 min)

In `manage.py shell`:

```python
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Passenger, User
from apps.core.enums import DeliveryStatus, RideMode, RideStatus, SOSStatus, UserRole
from apps.rides.models import Location, Ride, RideLeg, RideModeLookup
from apps.safety.models import SOSAlert, SOSNotification, TrustedContact

tricycle = RideModeLookup.objects.get(mode_code=RideMode.TRICYCLE)
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
Ride.objects.filter(pk=ride.pk).delete()
u.delete()
Location.objects.filter(pk__in=[a.pk, b.pk]).delete()
exit()
```

### 4. Commit (~10 min)

```powershell
Set-Location ..
git add backend/apps/safety/ docs/plan/design-freeze.md
git commit -m "feat(safety): add SOS alert, trusted contacts and notification fan-out"
git push
```

---

## Verify

- [ ] Three models migrated
- [ ] A duplicate contact mobile for the same passenger raises `IntegrityError`
- [ ] A duplicate `(alert, contact)` raises `IntegrityError`
- [ ] `alert.notifications.count()` equals the number of trusted contacts
- [ ] `mark_delivered()` sets the status and timestamp
- [ ] `notified_count` counts only delivered notifications
- [ ] `resolved_at` before `triggered_at` raises `IntegrityError`
- [ ] A second SOS on the same ride raises `IntegrityError`
- [ ] `response_seconds` returns `None` while open and an int once resolved
- [ ] The "SOS only during a ride" limitation is recorded in `docs/plan/design-freeze.md`
- [ ] Committed and pushed

---

## Log it

```markdown
**Step 2.07 — safety models — DONE**

- Added SOS_ALERT (1:0..1 on ride, position snapshotted not referenced),
  TRUSTED_CONTACT, SOS_NOTIFICATION (associative entity with per-contact
  delivery_status)
- Constraints: unique (passenger, contact_mobile), unique (alert, contact),
  resolved_at >= triggered_at
- Recorded limitation: SOS_ALERT.ride_id is NOT NULL, so an SOS can only be
  raised during a ride — noted in design-freeze.md
- Verified 6 checks in shell; all constraints enforced
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `fields.E304` on `SOSNotification` | The two FKs share a default `related_name` | They are `alert` and `contact` with distinct names — check you copied both |
| `Cannot resolve keyword 'ride'` on `SOSAlert` | `"rides.Ride"` spelled wrong | Check the app label |
| `timezone.timedelta` does not exist | It is `datetime.timedelta` | Import `from datetime import timedelta` |
| `notified_count` always 0 | Notifications are still `SENT` | Call `mark_delivered()`, or update the status |
| Cannot delete a ride that has an alert | `PROTECT` on `SOSAlert.ride` | Correct — an alert is evidence. Delete the alert first, deliberately |
| Deleting a contact removes notification history | `CASCADE` — intended | Documented in the class docstring |

---

## After this step

All 27 tables exist. Two steps remain in this phase, and they are the ones that make
the database usable: seeding the lookup data, and proving the constraints with real
tests.

Next: [08 — Migrations, seed data and admin](08-migrations-seed-and-admin.md)
