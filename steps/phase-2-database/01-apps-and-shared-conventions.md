# Step 2.01 — Apps and Shared Conventions

| | |
|---|---|
| **Goal** | Five Django apps exist; all 13 domain enums are written once; the UUID, money, coordinate and table-naming conventions are decided and encoded in abstract base models |
| **Day / Time** | Day 8 (Fri 13 Nov) · ~2 hours |
| **Prerequisites** | [Phase 1](../phase-1-repository/00-overview.md) complete |
| **Produces** | `backend/apps/` with `core/`, `accounts/`, `rides/`, `payments/`, `safety/` |

---

## Why an app layout step at all

You could put all 27 models in one app called `api`. It would work. It would also
mean a 2,000-line `models.py`, a 900-line `serializers.py`, and a `views.py` where
the matching engine, the payment adapter and the SOS handler are neighbours.

Five apps cost twenty minutes now and buy three things:

1. **Enums are defined once.** `RideStatus` is used by `rides` and by `safety` (an
   SOS alert can cancel a ride). In one app you would duplicate it or import across
   a circular boundary.
2. **Phase 3 splits along the same lines.** Each app gets its own serializers,
   views and tests, and the step files in Phase 3 map one-to-one onto them.
3. **The structure matches the domain.** `payments` containing every table that
   moves money is a sentence an assessor understands immediately.

---

## Do this

### 1. Create the `apps/` package and the five apps (~15 min)

Models live under `backend/apps/<name>/`, not at `backend/<name>/`. That keeps the
project root clean and makes `INSTALLED_APPS` read as a list of your own packages.

```powershell
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem\backend"
..\.venv\Scripts\Activate.ps1

New-Item -ItemType Directory -Force apps | Out-Null
New-Item -ItemType File -Force apps\__init__.py | Out-Null

Set-Location apps
python ..\manage.py startapp core
python ..\manage.py startapp accounts
python ..\manage.py startapp rides
python ..\manage.py startapp payments
python ..\manage.py startapp safety
Set-Location ..
```

`startapp` writes `migrations/__init__.py` for you, which is what makes the app
migratable. It does **not** write `apps.py` with the right `name` — check each one:

```python
# backend/apps/accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"          # ← must be the dotted path, not "accounts"
```

**This is the single most common mistake in this step.** `startapp accounts` writes
`name = "accounts"`, but the package is `apps.accounts`. Django then fails at startup
with `ModuleNotFoundError: No module named 'accounts'`. Fix all five files.

| App | `name` |
|---|---|
| core | `apps.core` |
| accounts | `apps.accounts` |
| rides | `apps.rides` |
| payments | `apps.payments` |
| safety | `apps.safety` |

### 2. Register the apps (~5 min)

In `backend/config/settings.py`, replace the default `INSTALLED_APPS` local section:

```python
INSTALLED_APPS = [
    # ── Django ─────────────────────────────────────────────────
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # ── Third party ────────────────────────────────────────────
    "rest_framework",
    "corsheaders",
    "drf_spectacular",

    # ── Sakay.ph ───────────────────────────────────────────────
    "apps.core",
    "apps.accounts",
    "apps.rides",
    "apps.payments",
    "apps.safety",
]
```

Prove it before writing a single model:

```powershell
python manage.py check
```

Expected: `System check identified no issues (0 silenced).` If it says
`ModuleNotFoundError`, re-read step 1's table.

### 3. Write all 13 domains as `TextChoices` (~45 min)

Create `backend/apps/core/enums.py`. **Every enum in the schema goes here, in one
file, once.** When `payments` needs `RideStatus` it imports it; it never redefines it.

```python
# backend/apps/core/enums.py
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
```

**Check the max_length values against the schema.** The `TextChoices` class itself
does not set a column width — that comes from the field in each model. The schema's
widths are:

| Enum | Schema width | Longest value | Fits? |
|---|---|---|---|
| `UserRole` | 12 | `PASSENGER` (9) | ✓ |
| `AccountStatus` | 12 | `DEACTIVATED` (11) | ✓ |
| `RideMode` | 12 | `HABAL_HABAL` (11) | ✓ |
| `RideStatus` | 16 | `DRIVER_EN_ROUTE` (15) | ✓ |
| `PaymentMethod` | 12 | `GCASH` (5) | ✓ |
| `PaymentStatus` | 16 | `PROCESSING` (10) | ✓ |
| `AccredStatus` | 12 | `SUSPENDED` (9) | ✓ |
| `SOSStatus` | 12 | `TRIGGERED` (9) | ✓ |
| `PayoutStatus` | 12 | `PROCESSING` (10) | ✓ |
| `SurgeTrigger` | 12 | `LGU_ADVISORY` (12) | ✓ **exactly 12 — no room** |
| `TxnType` | 12 | `DEDUCT` (6) | ✓ |
| `GroupStatus` | 12 | `DISPATCHED` (10) | ✓ |
| `DeliveryStatus` | 12 | `DELIVERED` (9) | ✓ |

`SurgeTrigger` at exactly 12 is the one to watch. If a future trigger value is
longer, that column needs widening — which is exactly why the width is written down
here rather than guessed per-model.

### 4. Write the shared abstract models (~30 min)

Create `backend/apps/core/models.py`:

```python
# backend/apps/core/models.py
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
```

**A note on why the model field is named `id`, not `user_id`.** The schema names
every PK after its entity (`user_id`, `ride_id`, …). Django convention is `id`, and
the column name is separate from the attribute name. Two options:

| Option | Field | Column | Trade-off |
|---|---|---|---|
| **A (chosen)** | `id` | `id` | Idiomatic Django; `ride.id` reads naturally in Python |
| B | `user_id` | `user_id` | Matches the schema document exactly; `user.user_id` is redundant |

This plan uses **A** and sets `db_table` to the schema's table name, so the
*database* still reads like the diagrams while the *Python* reads like Django. Note
the choice in the decision log — it is the kind of small inconsistency an assessor
may ask about.

### 5. Add `core` constants (~10 min)

Create `backend/apps/core/constants.py`:

```python
# backend/apps/core/constants.py
"""Tunable business constants.

Values that a real operator would change without a code deploy belong in
PLATFORM_CONFIG (a database table). Values that are structural belong here.
"""

from decimal import Decimal

# ── Matching ───────────────────────────────────────────────────
DEFAULT_SEARCH_RADIUS_KM = 3.0
MATCH_TIMEOUT_SECONDS = 90
MAX_CHAIN_LEGS = 4

# ── Money ──────────────────────────────────────────────────────
CURRENCY = "PHP"

# ── Simulated providers ────────────────────────────────────────
# No real gateway, SMS provider or GPS hardware is used anywhere in this
# project. These keep that visible in the code rather than implied.
SIMULATED_GATEWAY_PREFIX = "SIM-"
SIMULATED_OTP_LENGTH = 6
```

### 6. The `PLATFORM_CONFIG` table (D-62) (~20 min)

**Required — this is no longer conditional.** A-13 was decided on 11 Nov and recorded as
**D-62** in `database/consistency_report.md` §3.10: the commission rate goes in a
key-value table and the booking fee goes on `RIDE_MODE`. So this section and the
`booking_fee` column in [Step 03](03-models-accounts.md) §3 both land, and the design
goes from 26 tables to **27**.

The commission waiver in the mockups ("no commission on first 5 trips") needs
somewhere to live that is not a hard-coded constant.

```python
# append to backend/apps/core/models.py

class PlatformConfig(models.Model):
    """Key-value configuration an operator can change without a deploy.

    Deliberately untyped and unconstrained: the alternative is a column per
    setting, which means a migration every time a business rule changes.
    Readers are responsible for casting; the seed data documents the types.
    """

    key = models.CharField(max_length=60, primary_key=True)
    value = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "PLATFORM_CONFIG"
        verbose_name = "platform configuration"
        verbose_name_plural = "platform configuration"

    def __str__(self) -> str:
        return f"{self.key} = {self.value}"
```

Then, **before you migrate**, add the table to `database/schema_listing.md` as
table 27 and add `RIDE_MODE.booking_fee`. The design change comes first — that is
the rule from `CONTRIBUTING.md`.

**You do not write a new `consistency_report.md` entry for this.** A-13 was already
recorded as **D-62** on Day 5, when you decided it in
[Step 0.01](../phase-0-design-completion/01-complete-technology-stack.md). This step
is that decision being *implemented*, not a new decision. Update the D-62 entry's
status field to `implemented (Phase 2)` and leave the number alone.

Seed values for it land in [Step 08](08-migrations-seed-and-admin.md):

| key | value | meaning |
|---|---|---|
| `commission_rate` | `0.10` | Platform's cut of each fare |
| `commission_free_trips` | `5` | Trips before commission applies |
| `cancellation_fee` | `20.00` | Charged when a passenger cancels after matching |
| `sos_response_seconds` | `60` | Target time to notify all trusted contacts |

### 7. Prove it all loads (~10 min)

```powershell
python manage.py check
python -c "from apps.core.enums import RideStatus; print(list(RideStatus.values))"
```

Expected from the second command:

```
['REQUESTED', 'MATCHED', 'DRIVER_EN_ROUTE', 'ONGOING', 'COMPLETED', 'CANCELLED']
```

---

## Verify

```powershell
# Five apps exist with the right package name
Get-ChildItem apps -Directory | Select-Object Name
Select-String -Path apps\*\apps.py -Pattern 'name = '

# Django loads everything
python manage.py check

# The enums are importable and complete
python -c "from apps.core import enums; print(len([n for n in dir(enums) if not n.startswith('_')]))"
```

- [ ] `apps/` contains `core`, `accounts`, `rides`, `payments`, `safety`
- [ ] Every `apps.py` has `name = "apps.<app>"`, not `"<app>"`
- [ ] All five are in `INSTALLED_APPS`
- [ ] `apps/core/enums.py` defines all 13 domains
- [ ] `python manage.py check` reports no issues
- [ ] The enum import command prints the six `RideStatus` values
- [ ] `PLATFORM_CONFIG` exists with `key` as its primary key
- [ ] The schema listing and the consistency report were updated to carry table 27
      **before** the model was written (D-62)

---

## Log it

```markdown
**Step 2.01 — apps and shared conventions — DONE**

- Created apps/ with core, accounts, rides, payments, safety
- Fixed all five apps.py `name` attributes to the dotted path
- Wrote all 13 domains as TextChoices in apps/core/enums.py
- Added UUIDModel, TimeStampedModel, MoneyField, CoordinateField abstractions
- Decision: PK attribute named `id` (Django idiom) while db_table keeps the
  schema's UPPER_SNAKE name
- **D-62 (A-13):** PLATFORM_CONFIG added as table 27; schema_listing.md updated first
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'accounts'` | `apps.py` still has `name = "accounts"` | Change to `"apps.accounts"`. All five |
| `ModuleNotFoundError: No module named 'apps'` | `apps/__init__.py` missing | `New-Item -ItemType File apps\__init__.py` |
| `startapp` writes into the wrong folder | You ran it from `backend/` not `backend/apps/` | Delete the stray folder and re-run from `apps/` |
| `ImportError: cannot import name 'RideStatus' from 'apps.rides'` | You defined the enum in the app instead of `core` | Move it to `apps/core/enums.py`. Enums are defined once |
| Migration says `No changes detected` later | App has no `migrations/__init__.py` | Recreate the app, or add the file by hand |
| `MoneyField`/`CoordinateField` subclassing feels clever | It is mildly | If it causes trouble, replace with plain `DecimalField` and keep the convention in this document instead |

---

## After this step

You have a structure, not a schema. `python manage.py migrate` would still create
only Django's own tables. That changes in Step 02, when Django is pointed at MySQL,
and then in Steps 03–07 when the 27 models land.

Next: [02 — Settings, environment and database connection](02-settings-env-and-docker.md)
