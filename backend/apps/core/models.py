"""Shared abstract base models.

These carry no table of their own (``abstract = True``). They exist so that
every Sakay.ph model declares its primary key, timestamps and money fields
the same way, and so a reader can see the conventions in one place.
"""

import uuid

from django.db import models


class UUIDModel(models.Model):
    """Primary key as a UUID4.

    Django stores UUIDField as CHAR(32) on MySQL, which matches the
    ``UUID`` type used throughout database/schema_listing.md.

    Concrete models whose PK column must match the schema (per D-65) declare their
    own `id` field with `db_column="<entity>_id"` instead of inheriting this one.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Adds created/updated audit timestamps.

    Note: these are *audit* timestamps. Business timestamps that the schema
    names explicitly — RIDE.request_time, PAYMENT.paid_at, RATING.rated_at —
    are separate fields on those models, because their meaning is different
    from "when did this row change".
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class MoneyField(models.DecimalField):
    """A peso amount.

    Exists so no model can accidentally reach for FloatField. A fare that
    rounds the wrong way is a defect that cannot be explained to a user.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 10)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)


class CoordinateField(models.DecimalField):
    """A latitude or longitude.

    DECIMAL(9,6) gives ~11 cm of precision — far more than a phone GPS
    provides, and it stores exactly, unlike a float.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 9)
        kwargs.setdefault("decimal_places", 6)
        super().__init__(*args, **kwargs)


class PlatformConfig(models.Model):
    """Key-value configuration an operator can change without a deploy.

    Deliberately untyped and unconstrained: the alternative is a column per
    setting, which means a migration every time a business rule changes.
    Readers are responsible for casting; the seed data documents the types.
    """

    key = models.CharField(max_length=60, primary_key=True)
    value = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "PLATFORM_CONFIG"
        verbose_name = "platform configuration"
        verbose_name_plural = "platform configuration"

    def __str__(self) -> str:
        return f"{self.key} = {self.value}"