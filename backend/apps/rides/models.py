"""Ride-domain models.

Written incrementally across Steps 03-05. This step contributes only
RIDE_MODE, because Vehicle in the accounts app references it.
"""

from django.db import models

from apps.core.enums import RideMode


class RideModeLookup(models.Model):
    """The Lahat ng Sakayan mode list. Table 7.

    Named ``RideModeLookup`` rather than ``RideMode`` because
    ``apps.core.enums.RideMode`` already owns that name — and the enum is
    what every other model uses for its choices.
    """

    mode_code = models.CharField(
        max_length=12, primary_key=True, choices=RideMode.choices
    )
    mode_name = models.CharField(max_length=30)
    base_fare = models.DecimalField(max_digits=8, decimal_places=2)
    per_km_rate = models.DecimalField(max_digits=8, decimal_places=2)
    seat_capacity = models.SmallIntegerField()
    is_shared = models.BooleanField(
        default=False, help_text="Pakyawan-capable mode."
    )
    # ── D-62 (A-13) ────────────────────────────────────────────
    # Required. The mockups show a flat ₱3.00 booking fee on top of the metered
    # fare, and RIDE_MODE is where a per-mode flat fee belongs — one row changes
    # the price for every ride of that mode, with no code deploy.
    booking_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = "RIDE_MODE"
        verbose_name = "ride mode"
        verbose_name_plural = "ride modes"
        ordering = ["base_fare"]

    def __str__(self) -> str:
        return f"{self.mode_name} (₱{self.base_fare} + ₱{self.per_km_rate}/km)"
