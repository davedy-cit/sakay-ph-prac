# Step 2.08 — Migrations, Seed Data and Admin

| | |
|---|---|
| **Goal** | A fresh database reaches a fully usable state with two commands; all 27 tables are accounted for; every model is inspectable in the Django admin |
| **Day / Time** | Day 14 (Thu 19 Nov) · ~2.5 hours |
| **Prerequisites** | [Step 2.07](07-models-safety.md) |
| **Produces** | `seed_lookups` command, admin registrations, a verified 27-table schema, tag `v0.1.0` |

---

## Why seeding is not optional

Six ride modes, three payment methods and a handful of LGUs are **reference data**,
not user data. Without them:

- The booking screen has no modes to offer
- A fare cannot be calculated, because `RIDE_MODE.base_fare` has no rows
- No driver can be accredited, because `ACCREDITATION.lgu_code` has nothing to point at

Reference data is part of the schema in everything but name. The test for whether you
got this right is the M2 exit criterion: **`migrate` then `seed_lookups`, on a fresh
volume, with no manual SQL.**

---

## Do this

### 1. Confirm the migration set is clean (~15 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1

# No model change is waiting to be migrated
python manage.py makemigrations --check --dry-run

# What exists
python manage.py showmigrations
```

Expected: the first command prints `No changes detected`. If it lists changes, you
edited a model after migrating — generate the migration, do not hand-edit.

**On migration count.** You should have roughly one migration per app per step, so
about 10–12 files. That is fine. If you have 40, you ran `makemigrations` after every
model — squash them now while the database is disposable:

```powershell
# Optional, only if the count is unwieldy and no data matters yet
python manage.py squashmigrations accounts 0001 0004
```

Do not squash once real data exists. Today it is free.

### 2. Write the `seed_lookups` command (~60 min)

Create the directory structure:

```powershell
New-Item -ItemType Directory -Force apps\core\management\commands | Out-Null
New-Item -ItemType File -Force apps\core\management\__init__.py | Out-Null
New-Item -ItemType File -Force apps\core\management\commands\__init__.py | Out-Null
```

Both `__init__.py` files are required. Without them Django does not discover the
command and `manage.py seed_lookups` reports "Unknown command".

Create `backend/apps/core/management/commands/seed_lookups.py`:

```python
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
from apps.payments.models import PaymentMethodLookup
from apps.rides.models import RideModeLookup


# ── Lahat ng Sakyan: the six modes ─────────────────────────────
# Fares are indicative Philippine rates, not researched tariffs. They are
# rows rather than constants precisely so they can be tuned without a
# deploy — which is the point of FareCalculator.baseRates being a table.
RIDE_MODES = [
    {
        "mode_code": RideMode.TRICYCLE,
        "mode_name": "Tricycle",
        "base_fare": Decimal("25.00"),
        "per_km_rate": Decimal("12.00"),
        "seat_capacity": 3,
        "is_shared": False,
    },
    {
        "mode_code": RideMode.JEEPNEY,
        "mode_name": "Jeepney",
        "base_fare": Decimal("13.00"),
        "per_km_rate": Decimal("2.00"),
        "seat_capacity": 20,
        "is_shared": True,
    },
    {
        "mode_code": RideMode.UV_EXPRESS,
        "mode_name": "UV Express",
        "base_fare": Decimal("30.00"),
        "per_km_rate": Decimal("5.00"),
        "seat_capacity": 14,
        "is_shared": True,
    },
    {
        "mode_code": RideMode.HABAL_HABAL,
        "mode_name": "Habal-habal",
        "base_fare": Decimal("30.00"),
        "per_km_rate": Decimal("15.00"),
        "seat_capacity": 1,
        "is_shared": False,
    },
    {
        "mode_code": RideMode.ETRIKE,
        "mode_name": "E-Trike",
        "base_fare": Decimal("20.00"),
        "per_km_rate": Decimal("10.00"),
        "seat_capacity": 4,
        "is_shared": False,
    },
    {
        "mode_code": RideMode.CAR,
        "mode_name": "Car",
        "base_fare": Decimal("45.00"),
        "per_km_rate": Decimal("18.00"),
        "seat_capacity": 4,
        "is_shared": False,
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


class Command(BaseCommand):
    help = "Seed reference tables: ride modes, payment methods, LGU units."

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

        self.stdout.write(self.style.SUCCESS("Reference data seeded."))

    # ── Steps ──────────────────────────────────────────────────

    def _reset(self) -> None:
        # PROTECT on Vehicle.mode, Payment.method and Accreditation.lgu means
        # this raises rather than destroying referenced rows. That is correct.
        deleted = RideModeLookup.objects.all().delete()[0]
        deleted += PaymentMethodLookup.objects.all().delete()[0]
        deleted += LGUUnit.objects.all().delete()[0]
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

    def _report(self, kind: str, code: str, created: bool) -> None:
        verb = "created" if created else "updated"
        self.stdout.write(f"  {verb:8} {kind:16} {code}")
```

**`update_or_create` rather than `get_or_create`.** With `get_or_create`, editing a
fare in this file and re-running the command would silently do nothing — the row
already exists. `update_or_create` makes this file the source of truth for reference
data, which is what you want when you tune fares during Phase 4 testing.

### 3. Write the admin registrations (~40 min)

The admin is not decoration. It is how you will inspect the database during Phases
3–5 without writing a query, and how an assessor will see that the models are real.
It also takes twenty minutes for all five apps.

**`backend/apps/accounts/admin.py`**

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Accreditation, Driver, LGUUnit, Passenger, User, Vehicle


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """USER uses phone, not username, so the base class's fieldsets need
    rewriting — the defaults reference fields this model does not have."""

    ordering = ["full_name"]
    list_display = ["full_name", "phone", "user_role", "account_status", "is_staff"]
    list_filter = ["user_role", "account_status", "is_staff"]
    search_fields = ["full_name", "phone", "email"]
    readonly_fields = ["id", "last_login", "registration_date"]

    fieldsets = (
        (None, {"fields": ("id", "phone", "password")}),
        ("Personal", {"fields": ("full_name", "email")}),
        ("Sakay.ph", {"fields": ("user_role", "account_status", "registration_date")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "full_name", "user_role", "password1", "password2"),
            },
        ),
    )


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ["user", "home_address", "gcash_number", "verified_at"]
    search_fields = ["user__full_name", "user__phone", "gcash_number"]
    autocomplete_fields = ["user"]


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ["user", "license_number", "accreditation_status", "is_online",
                    "rating", "total_trips"]
    list_filter = ["accreditation_status", "is_online"]
    search_fields = ["user__full_name", "user__phone", "license_number"]
    autocomplete_fields = ["user"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["plate_number", "model", "mode", "driver", "capacity"]
    list_filter = ["mode"]
    search_fields = ["plate_number", "model", "driver__user__full_name"]
    autocomplete_fields = ["driver"]


@admin.register(LGUUnit)
class LGUUnitAdmin(admin.ModelAdmin):
    list_display = ["lgu_code", "lgu_name", "province", "region"]
    list_filter = ["region", "province"]
    search_fields = ["lgu_code", "lgu_name"]


@admin.register(Accreditation)
class AccreditationAdmin(admin.ModelAdmin):
    list_display = ["badge_no", "driver", "lgu", "status", "expiry_date", "badge_visible"]
    list_filter = ["status", "lgu", "badge_visible"]
    search_fields = ["badge_no", "driver__user__full_name"]
    autocomplete_fields = ["driver", "lgu"]
```

> **`autocomplete_fields` requires `search_fields` on the target admin.** If
> `VehicleAdmin` autocompletes `driver`, then `DriverAdmin` must define
> `search_fields` — it does above. Omitting it raises
> `admin.E040` at startup.

**`backend/apps/rides/admin.py`**

```python
from django.contrib import admin

from .models import (
    Cancellation, Location, PakyawanGroup, PassengerPreferredMode, Rating,
    Ride, RideLeg, RideModeLookup, SurgePeriod, TripTracking,
)


@admin.register(RideModeLookup)
class RideModeLookupAdmin(admin.ModelAdmin):
    list_display = ["mode_code", "mode_name", "base_fare", "per_km_rate",
                    "seat_capacity", "is_shared"]
    list_filter = ["is_shared"]
    search_fields = ["mode_code", "mode_name"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["street", "barangay", "city", "province", "landmark"]
    list_filter = ["city", "province"]
    search_fields = ["street", "barangay", "city", "landmark"]


class RideLegInline(admin.TabularInline):
    """Legs are edited inside the ride — a leg has no standalone identity,
    which is exactly what a weak entity means in a UI."""
    model = RideLeg
    extra = 0
    fields = ["leg_no", "mode", "driver", "origin_location", "dest_location",
              "fare", "distance_km", "eta_minutes", "surge", "status"]


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ["short_id", "passenger", "driver", "mode", "status",
                    "is_trip_chain", "leg_count", "fare_estimate", "request_time"]
    list_filter = ["status", "mode", "is_trip_chain"]
    search_fields = ["id", "passenger__user__full_name", "passenger__user__phone"]
    readonly_fields = ["id", "request_time"]
    autocomplete_fields = ["passenger", "driver", "vehicle", "mode",
                           "pickup_location", "dropoff_location"]
    inlines = [RideLegInline]
    date_hierarchy = "request_time"

    @admin.display(description="Ride")
    def short_id(self, obj):
        return str(obj.id)[:8]


@admin.register(RideLeg)
class RideLegAdmin(admin.ModelAdmin):
    list_display = ["ride", "leg_no", "mode", "driver", "fare", "status"]
    list_filter = ["status", "mode"]
    autocomplete_fields = ["ride", "mode", "driver", "origin_location",
                           "dest_location", "surge"]


@admin.register(SurgePeriod)
class SurgePeriodAdmin(admin.ModelAdmin):
    list_display = ["surge_label", "trigger_type", "multiplier", "lgu",
                    "starts_at", "ends_at", "is_active"]
    list_filter = ["trigger_type", "is_active", "lgu"]
    search_fields = ["surge_label"]


@admin.register(PakyawanGroup)
class PakyawanGroupAdmin(admin.ModelAdmin):
    list_display = ["direction", "ride", "matched_seats", "max_seats", "group_status"]
    list_filter = ["group_status"]
    autocomplete_fields = ["ride"]


@admin.register(PassengerPreferredMode)
class PassengerPreferredModeAdmin(admin.ModelAdmin):
    list_display = ["passenger", "mode", "preferred_rank"]
    autocomplete_fields = ["passenger", "mode"]


@admin.register(TripTracking)
class TripTrackingAdmin(admin.ModelAdmin):
    list_display = ["track_id", "ride", "latitude", "longitude", "recorded_at"]
    list_filter = ["recorded_at"]
    autocomplete_fields = ["ride"]


@admin.register(Cancellation)
class CancellationAdmin(admin.ModelAdmin):
    list_display = ["ride", "cancelled_by", "reason_code", "fee_amount",
                    "refund_amount", "cancelled_at"]
    list_filter = ["reason_code"]
    autocomplete_fields = ["ride", "cancelled_by"]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["ride", "rater_user", "ratee_user", "stars", "rated_at"]
    list_filter = ["stars"]
    search_fields = ["rater_user__full_name", "ratee_user__full_name"]
    autocomplete_fields = ["ride", "rater_user", "ratee_user"]
```

`TripTrackingAdmin` is registered for inspection only. In production you would not
list a high-volume ping table in the admin — add a note saying so if you like, since
it shows you know the difference between "registered" and "should be browsed".

**`backend/apps/payments/admin.py`**

```python
from django.contrib import admin

from .models import (
    DriverPayout, FareShare, Payment, PaymentMethodLookup, Receipt, Wallet, WalletTxn,
)


@admin.register(PaymentMethodLookup)
class PaymentMethodLookupAdmin(admin.ModelAdmin):
    list_display = ["method_code", "method_name", "is_digital", "gateway_name"]
    list_filter = ["is_digital"]
    search_fields = ["method_code", "method_name"]


class WalletTxnInline(admin.TabularInline):
    model = WalletTxn
    extra = 0
    fields = ["txn_type", "amount", "balance_after", "gateway_ref", "created_at"]
    readonly_fields = ["created_at"]
    can_delete = False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ["passenger", "balance", "currency", "updated_at"]
    search_fields = ["passenger__user__full_name", "passenger__user__phone"]
    autocomplete_fields = ["passenger"]
    inlines = [WalletTxnInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["short_id", "ride", "payer", "method", "amount", "status", "paid_at"]
    list_filter = ["status", "method"]
    search_fields = ["id", "gateway_ref", "payer__user__full_name"]
    autocomplete_fields = ["ride", "payer", "method", "wallet"]
    date_hierarchy = "paid_at"

    @admin.display(description="Payment")
    def short_id(self, obj):
        return str(obj.id)[:8]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["receipt_no", "payment", "total_amount", "issued_at"]
    search_fields = ["receipt_no"]
    autocomplete_fields = ["payment"]


@admin.register(FareShare)
class FareShareAdmin(admin.ModelAdmin):
    list_display = ["payment", "passenger", "group", "passenger_count",
                    "share_amount", "is_paid"]
    list_filter = ["is_paid"]
    autocomplete_fields = ["payment", "passenger", "group"]


@admin.register(WalletTxn)
class WalletTxnAdmin(admin.ModelAdmin):
    list_display = ["wallet", "txn_type", "amount", "balance_after",
                    "gateway_ref", "created_at"]
    list_filter = ["txn_type"]
    autocomplete_fields = ["wallet", "payment"]


@admin.register(DriverPayout)
class DriverPayoutAdmin(admin.ModelAdmin):
    list_display = ["driver", "method", "amount", "status", "requested_at", "paid_at"]
    list_filter = ["status", "method"]
    autocomplete_fields = ["driver", "method"]
```

**`backend/apps/safety/admin.py`**

```python
from django.contrib import admin

from .models import SOSAlert, SOSNotification, TrustedContact


@admin.register(TrustedContact)
class TrustedContactAdmin(admin.ModelAdmin):
    list_display = ["contact_name", "passenger", "contact_mobile", "relationship"]
    search_fields = ["contact_name", "contact_mobile", "passenger__user__full_name"]
    autocomplete_fields = ["passenger"]


class SOSNotificationInline(admin.TabularInline):
    model = SOSNotification
    extra = 0
    fields = ["contact", "delivery_status", "notified_at"]
    autocomplete_fields = ["contact"]


@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
    list_display = ["short_id", "ride", "raised_by", "alert_type", "status",
                    "triggered_at", "resolved_at"]
    list_filter = ["status", "alert_type"]
    search_fields = ["id", "ride__id", "raised_by__full_name"]
    readonly_fields = ["id", "triggered_at"]
    autocomplete_fields = ["ride", "raised_by"]
    inlines = [SOSNotificationInline]
    date_hierarchy = "triggered_at"

    @admin.display(description="Alert")
    def short_id(self, obj):
        return str(obj.id)[:8]


@admin.register(SOSNotification)
class SOSNotificationAdmin(admin.ModelAdmin):
    list_display = ["alert", "contact", "delivery_status", "notified_at"]
    list_filter = ["delivery_status"]
    autocomplete_fields = ["alert", "contact"]
```

**`backend/apps/core/admin.py`**

```python
from django.contrib import admin

from .models import PlatformConfig


@admin.register(PlatformConfig)
class PlatformConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "description", "updated_at"]
    search_fields = ["key", "description"]
```

No `try/except ImportError` guard: `PlatformConfig` is required as of **D-62**, so a
missing model is a real error and should surface as one rather than silently skipping
the registration.

### 4. Prove the whole thing from scratch (~30 min)

This is the M2 exit criterion, run literally. **It destroys your data — which is
fine, because nothing in it is real yet.**

```powershell
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem"
docker compose down -v
docker compose up -d
# wait for MySQL to report healthy
docker compose ps

Set-Location backend
..\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py seed_lookups
python manage.py seed_lookups      # run twice — must be idempotent
```

The second run must print `updated` for every row and create nothing new.

Then count the tables:

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW TABLES;"
```

Cross-check against `database/schema_listing.md`. All 27 application tables must be
present. Rather than eyeball a wall of names, count them:

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -N -e "
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema='sakayph'
  AND table_name NOT LIKE 'django\_%'
  AND table_name NOT LIKE 'auth\_%';"
```

Expected: **27** — 26 from the original design plus `PLATFORM_CONFIG`, which **D-62**
added on 11 Nov.

Then list them and tick each one off against `schema_listing.md`:

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -N -e "
SELECT table_name FROM information_schema.tables
WHERE table_schema='sakayph'
  AND table_name NOT LIKE 'django\_%'
  AND table_name NOT LIKE 'auth\_%'
ORDER BY table_name;"
```

**Export the DDL as a readable artifact** (~5 min). Audit finding **A-04** observed
that the design phase deliberately generated no SQL, which left nothing a marker
could read to see the schema. Migrations are the DDL now — this just writes them out
in a form a person can read without running anything.

```powershell
docker compose exec -T mysql mysqldump -u root -prootpass `
  --no-data --skip-comments --skip-add-drop-table --compact sakayph `
  > docs/schema.sql
```

Then strip the framework's own tables so the file shows only your 27:

```powershell
$keep = Select-String -Path docs/schema.sql -Pattern '^CREATE TABLE `(?!django_|auth_)' -AllMatches
"$($keep.Matches.Count) application tables in docs/schema.sql"
```

Expected: **27**.

Commit `docs/schema.sql`. **Note what this file is and is not:** it is a
point-in-time snapshot for a reader, *not* the source of truth. Migrations remain
the source of truth, and nothing generates code from this file. Say so in the README
so nobody edits it by hand and expects the database to follow.

**Prove the encoding survived the rebuild** — the `ñ` in Biñan is the test:

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SELECT lgu_code, lgu_name FROM LGU_UNIT WHERE lgu_code='BIN-LAG';"
```

Expected: `BIN-LAG   City of Biñan`. A `?` means the collation is wrong.

Then the admin:

```powershell
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/` and confirm all 27 models are listed and openable.
A model that raises a 500 on its list page usually has a broken `list_display` or a
missing `search_fields` for an autocomplete.

### 5. Update the README and tag (~25 min)

The root README's "Running it" section was an honest placeholder in Step 0.02. Replace
it with the real commands:

````markdown
## Running it

Requires Docker Desktop, Python 3.14 and Node 24.

```powershell
# 1. Services
docker compose up -d

# 2. Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements/dev.txt
Copy-Item .env.example .env      # then fill in the values
Set-Location backend
python manage.py migrate
python manage.py seed_lookups
python manage.py createsuperuser
python manage.py runserver       # http://127.0.0.1:8000

# 3. Frontend (second terminal)
Set-Location frontend
npm install
npm run dev                      # http://127.0.0.1:5173
```
````

Then tag the milestone:

```powershell
Set-Location ..
git add .
git commit -m "feat(db): seed reference data, register admin, verify full schema"
git tag -a v0.1.0 -m "Database and domain model complete — 27 tables migrated and seeded"
git push
git push origin v0.1.0
```

`CONTRIBUTING.md` reserves `v0.1.0` for exactly this point. Milestone **M2 is now met.**

---

## Verify

- [ ] `makemigrations --check --dry-run` reports no changes
- [ ] `migrate` then `seed_lookups` on a fresh volume works with no manual SQL
- [ ] Running `seed_lookups` twice creates nothing new
- [ ] All 27 application tables exist
- [ ] `City of Biñan` reads back with the `ñ` intact
- [ ] All 27 models open in the admin without error
- [ ] A `Ride`'s legs are editable inline in the admin
- [ ] A `Wallet`'s ledger is visible inline
- [ ] The README's "Running it" section is real, not a placeholder
- [ ] `v0.1.0` is tagged and pushed
- [ ] M2 exit criterion met

---

## Log it

```markdown
**Step 2.08 — migrations, seed and admin — DONE**

- Added seed_lookups command: 6 ride modes, 3 payment methods, 4 LGU units;
  idempotent via update_or_create, --reset available
- Registered all 27 models in the admin with list_display/filters/search,
  RideLeg inline on Ride, WalletTxn inline on Wallet, SOSNotification inline
  on SOSAlert, PlatformConfig searchable by key
- Full rebuild verified: down -v, up, migrate, seed_lookups x2 — 27 tables,
  Biñan ñ intact
- README "Running it" replaced with real commands
- **Tag:** v0.1.0
- **Milestone M2: MET**
```

Then in `steps/PROGRESS.md`: tick the Phase 2 block, and add the tag to the daily log.

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `Unknown command: 'seed_lookups'` | Missing `__init__.py` in `management/` or `management/commands/` | Create both |
| `admin.E040` | `autocomplete_fields` on a target with no `search_fields` | Add `search_fields` to the target admin |
| `admin.E108` | `list_display` names a method that does not exist | Check the `@admin.display` methods are defined |
| Admin user page 500s | `UserAdmin` fieldsets reference `username` | Use the rewritten fieldsets above |
| `seed_lookups` says "created" every run | `update_or_create` returning created=True because the PK differs | The `mode_code` in the file must match the `mode_code` in the row |
| `Cannot delete ... PROTECT` on `--reset` | Real data references the lookups | Correct behaviour. Drop the volume instead |
| Only 26 tables | `PLATFORM_CONFIG` absent | You skipped Step 2.01 §6. It is required as of D-62 — add the model and re-migrate |
| `?` instead of `ñ` | Collation regressed | `docker compose down -v`, confirm the `command:` block in `docker-compose.yml`, `up -d` |
| Squash produced a broken migration | Squashed across a dependency | `git checkout` the migrations folder and skip squashing — it is optional |

---

## After this step

The database is real, seeded and browsable. One step left in this phase, and it is the
one that turns "the design says so" into "the implementation proves it": tests.

Next: [09 — Model tests](09-model-tests.md)
