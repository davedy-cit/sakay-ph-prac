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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="contact_id")

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="alert_id")

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
