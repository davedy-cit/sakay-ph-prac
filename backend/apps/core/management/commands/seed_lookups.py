# backend/apps/core/management/commands/seed_lookups.py
"""Seed the reference tables.

Idempotent: running it twice changes nothing. That matters because it runs
in the README's setup instructions, in CI, and every time someone resets
their database.

    python manage.py seed_lookups
    python manage.py seed_lookups --reset   # delete and re-create
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import LGUUnit
from apps.core.enums import PaymentMethod, RideMode
from apps.core.models import PlatformConfig
from apps.payments.models import PaymentMethodLookup
from apps.rides.models import RideModeLookup


# ── Lahat ng Sakyan: the six modes ─────────────────────────────
# Fares are indicative Philippine rates, not researched tariffs. They are
# rows rather than constants precisely so they can be tuned without a
# deploy — which is the point of FareCalculator.baseRates being a table.
# booking_fee is decided, not indicative: ₱3.00 flat on every mode (D-64),
# charged once per RIDE — never multiplied by the leg count.
RIDE_MODES = [
    {
        "mode_code": RideMode.TRICYCLE,
        "mode_name": "Tricycle",
        "base_fare": Decimal("25.00"),
        "per_km_rate": Decimal("12.00"),
        "seat_capacity": 3,
        "is_shared": False,
        "booking_fee": Decimal("3.00"),
    },
    {
        "mode_code": RideMode.JEEPNEY,
        "mode_name": "Jeepney",
        "base_fare": Decimal("13.00"),
        "per_km_rate": Decimal("2.00"),
        "seat_capacity": 20,
        "is_shared": True,
        "booking_fee": Decimal("3.00"),
    },
    {
        "mode_code": RideMode.UV_EXPRESS,
        "mode_name": "UV Express",
        "base_fare": Decimal("30.00"),
        "per_km_rate": Decimal("5.00"),
        "seat_capacity": 14,
        "is_shared": True,
        "booking_fee": Decimal("3.00"),
    },
    {
        "mode_code": RideMode.HABAL_HABAL,
        "mode_name": "Habal-habal",
        "base_fare": Decimal("30.00"),
        "per_km_rate": Decimal("15.00"),
        "seat_capacity": 1,
        "is_shared": False,
        "booking_fee": Decimal("3.00"),
    },
    {
        "mode_code": RideMode.ETRIKE,
        "mode_name": "E-Trike",
        "base_fare": Decimal("20.00"),
        "per_km_rate": Decimal("10.00"),
        "seat_capacity": 4,
        "is_shared": False,
        "booking_fee": Decimal("3.00"),
    },
    {
        "mode_code": RideMode.CAR,
        "mode_name": "Car",
        "base_fare": Decimal("45.00"),
        "per_km_rate": Decimal("18.00"),
        "seat_capacity": 4,
        "is_shared": False,
        "booking_fee": Decimal("3.00"),
    },
]

PAYMENT_METHODS = [
    {
        "method_code": PaymentMethod.GCASH,
        "method_name": "GCash",
        "is_digital": True,
        "gateway_name": "GCash",
    },
    {
        "method_code": PaymentMethod.MAYA,
        "method_name": "Maya",
        "is_digital": True,
        "gateway_name": "Maya",
    },
    {
        "method_code": PaymentMethod.CASH,
        "method_name": "Cash",
        "is_digital": False,
        "gateway_name": "",
    },
]

# Note the ñ in Biñan — deliberately included so a latin1 database fails
# loudly here rather than silently mangling a name in Phase 4.
LGU_UNITS = [
    {
        "lgu_code": "CBO-LAG",
        "lgu_name": "City of Cabuyao",
        "province": "Laguna",
        "region": "CALABARZON",
        "contact_no": "(049) 531-0000",
    },
    {
        "lgu_code": "STA-LAG",
        "lgu_name": "City of Santa Rosa",
        "province": "Laguna",
        "region": "CALABARZON",
        "contact_no": "(049) 534-0000",
    },
    {
        "lgu_code": "CAL-LAG",
        "lgu_name": "City of Calamba",
        "province": "Laguna",
        "region": "CALABARZON",
        "contact_no": "(049) 545-0000",
    },
    {
        "lgu_code": "BIN-LAG",
        "lgu_name": "City of Biñan",
        "province": "Laguna",
        "region": "CALABARZON",
        "contact_no": "(049) 511-0000",
    },
]

# D-62 (A-13): the four keys `schema_listing.md` §27 documents. Values stay
# strings — readers cast, per the PlatformConfig docstring.
PLATFORM_CONFIG = [
    {"key": "commission_rate", "value": "0.10", "description": "Platform's cut of each fare"},
    {"key": "commission_free_trips", "value": "5", "description": "Trips before commission applies"},
    {"key": "cancellation_fee", "value": "20.00", "description": "Charged when a passenger cancels after matching"},
    {"key": "sos_response_seconds", "value": "60", "description": "Target time to notify all trusted contacts"},
]


class Command(BaseCommand):
    help = "Seed reference tables: ride modes, payment methods, LGU units, platform config."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing reference rows first. Fails if anything references them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        self._seed_ride_modes()
        self._seed_payment_methods()
        self._seed_lgu_units()
        self._seed_platform_config()

        self.stdout.write(self.style.SUCCESS("Reference data seeded."))

    # ── Steps ──────────────────────────────────────────────────

    def _reset(self) -> None:
        # PROTECT on Vehicle.mode, Payment.method and Accreditation.lgu means
        # this raises rather than destroying referenced rows. That is correct.
        deleted = RideModeLookup.objects.all().delete()[0]
        deleted += PaymentMethodLookup.objects.all().delete()[0]
        deleted += LGUUnit.objects.all().delete()[0]
        deleted += PlatformConfig.objects.all().delete()[0]
        self.stdout.write(f"  reset: removed {deleted} rows")

    def _seed_ride_modes(self) -> None:
        for row in RIDE_MODES:
            code = row["mode_code"]
            _, created = RideModeLookup.objects.update_or_create(
                mode_code=code, defaults=row
            )
            self._report("ride mode", code, created)

    def _seed_payment_methods(self) -> None:
        for row in PAYMENT_METHODS:
            code = row["method_code"]
            _, created = PaymentMethodLookup.objects.update_or_create(
                method_code=code, defaults=row
            )
            self._report("payment method", code, created)

    def _seed_lgu_units(self) -> None:
        for row in LGU_UNITS:
            code = row["lgu_code"]
            _, created = LGUUnit.objects.update_or_create(lgu_code=code, defaults=row)
            self._report("LGU unit", code, created)

    def _seed_platform_config(self) -> None:
        for row in PLATFORM_CONFIG:
            _, created = PlatformConfig.objects.update_or_create(
                key=row["key"], defaults=row
            )
            self._report("platform config", row["key"], created)

    def _report(self, kind: str, code: str, created: bool) -> None:
        verb = "created" if created else "updated"
        self.stdout.write(f"  {verb:8} {kind:16} {code}")
