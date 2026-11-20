"""Schema contract tests.

Asserts that the migrated database matches database/schema_listing.md and the
design decisions recorded in consistency_report.md. If one of these fails, the
document and the database have drifted apart — which is the one failure mode a
design-first project cannot tolerate.
"""

import pytest
from django.db import connection

# Both marks: `contract` tags the suite for `pytest -m contract`; `django_db`
# is what actually grants database access — a bare custom marker does not.
pytestmark = [pytest.mark.contract, pytest.mark.django_db]


# ── The 27 tables ──────────────────────────────────────────────

# Written out rather than derived from the models, so that a typo in a
# model's db_table is caught instead of being compared against itself.
DOCUMENTED_TABLES = [
    "ACCREDITATION", "CANCELLATION", "DRIVER", "DRIVER_PAYOUT", "FARE_SHARE",
    "LGU_UNIT", "LOCATION", "PAKYAWAN_GROUP", "PASSENGER",
    "PASSENGER_PREFERRED_MODE", "PAYMENT", "PAYMENT_METHOD", "PLATFORM_CONFIG",
    "RATING", "RECEIPT",
    "RIDE", "RIDE_LEG", "RIDE_MODE", "SOS_ALERT", "SOS_NOTIFICATION",
    "SURGE_PERIOD", "TRIP_TRACKING", "TRUSTED_CONTACT", "USER", "VEHICLE",
    "WALLET", "WALLET_TXN",
]


def _app_tables() -> set[str]:
    """Table names in the current schema, excluding Django's own.

    Three exclusions, not two: ``django_%`` and ``auth_%`` are the
    framework's migrations/sessions/content-type tables, and ``USER_%`` is
    where the M2M tables for the custom user land — Django names them after
    the model's *db_table* (``USER_groups``, ``USER_user_permissions``), not
    the app label, so they do not match ``auth_%``.
    """
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name NOT LIKE 'django\\_%'
              AND table_name NOT LIKE 'auth\\_%'
              AND table_name NOT LIKE 'USER\\_%'
            """
        )
        return {row[0] for row in cur.fetchall()}


def test_all_documented_tables_exist():
    assert len(DOCUMENTED_TABLES) == 27, "27 tables: the original 26 plus PLATFORM_CONFIG (D-62)"
    missing = set(DOCUMENTED_TABLES) - _app_tables()
    assert not missing, f"documented but not migrated: {sorted(missing)}"


def test_no_undocumented_tables_exist():
    """Catches a model whose db_table was never added to the design."""
    extra = _app_tables() - set(DOCUMENTED_TABLES)
    assert not extra, f"migrated but not documented: {sorted(extra)}"


# ── Composite keys implemented as UNIQUE constraints ───────────

def _unique_indexes(table: str) -> set[frozenset]:
    """Each unique index in `table`, as a frozenset of column names."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT index_name, GROUP_CONCAT(column_name ORDER BY seq_in_index)
            FROM information_schema.statistics
            WHERE table_schema = DATABASE() AND table_name = %s AND non_unique = 0
            GROUP BY index_name
            """,
            [table],
        )
        return {frozenset(cols.split(",")) for _, cols in cur.fetchall()}


@pytest.mark.parametrize(
    "table,columns,constraint",
    [
        ("RIDE_LEG", {"ride_id", "leg_no"}, "uq_rideleg_ride_legno"),
        ("FARE_SHARE", {"payment_id", "passenger_id"}, "uq_fareshare_payment_passenger"),
        ("SOS_NOTIFICATION", {"alert_id", "contact_id"}, "uq_sosnotif_alert_contact"),
        ("PASSENGER_PREFERRED_MODE", {"passenger_id", "mode_code"},
         "uq_prefmode_passenger_mode"),
    ],
)
def test_composite_key_is_enforced(table, columns, constraint):
    """The four documented composite keys, implemented as unique indexes.

    This is the deviation recorded in consistency_report.md: Django has no
    composite primary key, so uniqueness carries the guarantee instead.
    """
    indexes = _unique_indexes(table)
    assert frozenset(columns) in indexes, (
        f"{table} has no UNIQUE index on {sorted(columns)}; found {indexes}"
    )


@pytest.mark.parametrize(
    "table,columns",
    [
        ("USER", {"phone"}),
        ("PAYMENT", {"ride_id"}),
        ("RECEIPT", {"payment_id"}),
        ("PAKYAWAN_GROUP", {"ride_id"}),
        ("SOS_ALERT", {"ride_id"}),
        ("CANCELLATION", {"ride_id"}),
        ("WALLET", {"passenger_id"}),
        ("VEHICLE", {"driver_id"}),
        ("DRIVER", {"license_number"}),
        ("ACCREDITATION", {"badge_no"}),
    ],
)
def test_one_to_one_and_unique_columns(table, columns):
    """Every 1 : 0..1 in the schema is a UNIQUE constraint in the database."""
    assert frozenset(columns) in _unique_indexes(table), (
        f"{table} is missing UNIQUE on {sorted(columns)}"
    )


# ── Enumerated columns are wide enough ─────────────────────────

@pytest.mark.parametrize(
    "table,column,width",
    [
        ("USER", "user_role", 12),
        ("USER", "account_status", 12),
        ("RIDE", "status", 16),
        ("RIDE_LEG", "status", 16),
        ("DRIVER", "accreditation_status", 12),
        ("SURGE_PERIOD", "trigger_type", 12),
        ("PAYMENT", "status", 16),
        ("WALLET_TXN", "txn_type", 12),
        ("SOS_ALERT", "status", 12),
        ("SOS_NOTIFICATION", "delivery_status", 12),
        ("PAKYAWAN_GROUP", "group_status", 12),
        ("DRIVER_PAYOUT", "status", 12),
    ],
)
def test_enum_column_width_matches_the_schema(table, column, width):
    """A column one character too narrow silently truncates a status value."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT character_maximum_length FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
            """,
            [table, column],
        )
        row = cur.fetchone()
    assert row is not None, f"{table}.{column} does not exist"
    assert row[0] == width, f"{table}.{column} is VARCHAR({row[0]}), expected {width}"


def test_every_enum_value_fits_its_column():
    """The width table in schema_listing.md, checked against the enum itself."""
    from apps.core import enums

    widths = {
        "UserRole": 12, "AccountStatus": 12, "RideMode": 12, "RideStatus": 16,
        "PaymentMethod": 12, "PaymentStatus": 16, "AccredStatus": 12,
        "SOSStatus": 12, "PayoutStatus": 12, "SurgeTrigger": 12, "TxnType": 12,
        "GroupStatus": 12, "DeliveryStatus": 12,
    }
    for name, width in widths.items():
        enum_cls = getattr(enums, name)
        longest = max(len(v) for v in enum_cls.values)
        assert longest <= width, (
            f"{name}.{max(enum_cls.values, key=len)} is {longest} chars "
            f"but the column is VARCHAR({width})"
        )


# ── Money is never a float ─────────────────────────────────────

def test_no_float_columns_for_money():
    """A fare stored as a float rounds wrong in ways you cannot explain."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND (column_name LIKE '%%fare%%' OR column_name LIKE '%%amount%%'
                   OR column_name LIKE '%%balance%%' OR column_name LIKE '%%rate%%'
                   OR column_name LIKE '%%fee%%')
            """
        )
        offenders = [
            (t, c, d) for t, c, d in cur.fetchall()
            if d in ("float", "double", "real")
        ]
    assert not offenders, f"money columns stored as float: {offenders}"


# ── Encoding ───────────────────────────────────────────────────

def test_connection_charset_is_utf8mb4():
    """Tagalog diacritics and the mode emoji both need 4-byte UTF-8."""
    with connection.cursor() as cur:
        cur.execute("SHOW VARIABLES LIKE 'character_set_connection'")
        assert cur.fetchone()[1] == "utf8mb4"


def test_non_ascii_round_trips(db):
    """The ñ in Biñan and the peso sign in a fare label."""
    from apps.accounts.models import LGUUnit

    LGUUnit.objects.create(lgu_code="BIN-LAG", lgu_name="City of Biñan",
                           province="Laguna", region="CALABARZON")
    assert LGUUnit.objects.get(lgu_code="BIN-LAG").lgu_name == "City of Biñan"


# ── Soft checks against the design documents ───────────────────

def test_rating_points_at_user_twice():
    """The unary relationship, in the DDL."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, referenced_table_name
            FROM information_schema.key_column_usage
            WHERE table_schema = DATABASE() AND table_name = 'RATING'
              AND referenced_table_name IS NOT NULL
            """
        )
        refs = dict(cur.fetchall())
    assert refs.get("rater_user_id") == "USER"
    assert refs.get("ratee_user_id") == "USER"


def test_passenger_pk_is_also_a_foreign_key():
    """Class-table inheritance: the subtype PK is the supertype FK."""
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, referenced_table_name
            FROM information_schema.key_column_usage
            WHERE table_schema = DATABASE() AND table_name = 'PASSENGER'
              AND referenced_table_name IS NOT NULL
            """
        )
        refs = dict(cur.fetchall())
    assert refs.get("passenger_id") == "USER"


def test_driver_earnings_are_not_in_the_passenger_wallet():
    """TxnType has no PAYOUT, and DRIVER_PAYOUT exists instead."""
    from apps.core.enums import TxnType

    assert "PAYOUT" not in TxnType.values
    assert "DRIVER_PAYOUT" in _app_tables()
