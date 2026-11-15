"""Domain enumerations for Sakay.ph.

Every enumerated value in database/schema_listing.md lives here exactly once.
They are stored as short VARCHAR codes rather than MySQL ENUM types, so a new
ride mode or payment status can be added without a schema migration — which
matters for a platform whose mode list is explicitly open-ended.
"""

from django.db import models


class UserRole(models.TextChoices):
    """Discriminator for the USER specialization (disjoint, total)."""

    PASSENGER = "PASSENGER", "Passenger"
    DRIVER = "DRIVER", "Driver"
    ADMIN = "ADMIN", "Administrator"


class AccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    DEACTIVATED = "DEACTIVATED", "Deactivated"


class RideMode(models.TextChoices):
    """The Lahat ng Sakyan mode list."""

    TRICYCLE = "TRICYCLE", "Tricycle"
    JEEPNEY = "JEEPNEY", "Jeepney"
    UV_EXPRESS = "UV_EXPRESS", "UV Express"
    HABAL_HABAL = "HABAL_HABAL", "Habal-habal"
    ETRIKE = "ETRIKE", "E-Trike"
    CAR = "CAR", "Car"


class RideStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    MATCHED = "MATCHED", "Matched"
    DRIVER_EN_ROUTE = "DRIVER_EN_ROUTE", "Driver en route"
    ONGOING = "ONGOING", "Ongoing"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentMethod(models.TextChoices):
    GCASH = "GCASH", "GCash"
    MAYA = "MAYA", "Maya"
    CASH = "CASH", "Cash"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    REFUNDED = "REFUNDED", "Refunded"
    FAILED = "FAILED", "Failed"


class AccredStatus(models.TextChoices):
    """Sertipikadong Manong accreditation state."""

    PENDING = "PENDING", "Pending"
    VERIFIED = "VERIFIED", "Verified"
    EXPIRED = "EXPIRED", "Expired"
    SUSPENDED = "SUSPENDED", "Suspended"


class SOSStatus(models.TextChoices):
    TRIGGERED = "TRIGGERED", "Triggered"
    NOTIFIED = "NOTIFIED", "Contacts notified"
    RESPONDING = "RESPONDING", "Responding"
    RESOLVED = "RESOLVED", "Resolved"
    CANCELLED = "CANCELLED", "Cancelled"


class PayoutStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    PROCESSING = "PROCESSING", "Processing"
    PAID = "PAID", "Paid"
    FAILED = "FAILED", "Failed"


class SurgeTrigger(models.TextChoices):
    """Bagyo Mode trigger source."""

    WEATHER = "WEATHER", "Weather"
    DEMAND = "DEMAND", "Demand"
    MANUAL = "MANUAL", "Manual"
    LGU_ADVISORY = "LGU_ADVISORY", "LGU advisory"


class TxnType(models.TextChoices):
    """Wallet ledger entry type.

    Deliberately has no PAYOUT value: driver earnings are not a
    passenger-wallet transaction and live in DRIVER_PAYOUT instead.
    """

    TOPUP = "TOPUP", "Top-up"
    DEDUCT = "DEDUCT", "Deduction"
    REFUND = "REFUND", "Refund"


class GroupStatus(models.TextChoices):
    """Pakyawan share-ride group state."""

    FORMING = "FORMING", "Forming"
    FULL = "FULL", "Full"
    DISPATCHED = "DISPATCHED", "Dispatched"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class DeliveryStatus(models.TextChoices):
    """Per-contact state of an SOS notification."""

    SENT = "SENT", "Sent"
    DELIVERED = "DELIVERED", "Delivered"
    FAILED = "FAILED", "Failed"