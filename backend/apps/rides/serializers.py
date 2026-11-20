"""Ride-domain API serializers.

`Location` is the booking screens' write path; the lookups are read-only
because their rows are reference data owned by seed_lookups and the admin.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.accounts.models import LGUUnit
from apps.rides.models import Location, RideModeLookup


class LocationSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        min_value=Decimal("-90"), max_value=Decimal("90"),
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        min_value=Decimal("-180"), max_value=Decimal("180"),
    )

    class Meta:
        model = Location
        fields = ["id", "street", "barangay", "city", "province",
                  "landmark", "latitude", "longitude"]
        read_only_fields = ["id"]


class RideModeSerializer(serializers.ModelSerializer):
    """Read-only exposure of the Lahat ng Sakyan rate card.

    booking_fee is D-64's ₱3.00 flat, read from the seeded row — rates are
    data (D-62), never code, and never edited through the API.
    """

    class Meta:
        model = RideModeLookup
        fields = ["mode_code", "mode_name", "base_fare", "per_km_rate",
                  "seat_capacity", "is_shared", "booking_fee"]


class LGUUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = LGUUnit
        fields = ["lgu_code", "lgu_name", "province", "region", "contact_no"]