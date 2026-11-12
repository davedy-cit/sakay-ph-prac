# Step 2.03 — Models: Accounts

| | |
|---|---|
| **Goal** | USER, PASSENGER, DRIVER, VEHICLE, LGU_UNIT and ACCREDITATION exist as tables, with phone-based login and class-table inheritance |
| **Day / Time** | Day 10 (Sun 15 Nov) · ~3 hours |
| **Prerequisites** | [Step 2.02](02-settings-env-and-docker.md) |
| **Produces** | `backend/apps/accounts/models.py`, `AUTH_USER_MODEL` set, accounts migration |

---

## The decision this step forces

Django's authentication framework wants to own the user table. Your schema already
has one — `USER`, with `password_hash`, a `user_role` discriminator, and no
`username`. Three ways to reconcile that:

| Option | What it means | Verdict |
|---|---|---|
| **A — `AUTH_USER_MODEL = "accounts.User"`** | Your USER table *is* Django's user model. Gains `last_login`, `is_staff`, `is_superuser` and two M2M join tables | **Chosen** |
| B — keep `auth.User` for admin, `accounts.User` for the domain | Two identity systems. `request.user` means different things in different views | Rejected — a bug factory |
| C — no Django auth at all, hand-rolled JWT | Reimplements password hashing, permissions and the admin | Rejected — weeks of work for nothing |

**Option A is a design change and must be recorded before you write the code.** The
procedure from `CONTRIBUTING.md`:

1. Add three columns to `USER` in `database/schema_listing.md`:
   `last_login DATETIME NULL`, `is_staff BOOLEAN NOT NULL DEFAULT 0`,
   `is_superuser BOOLEAN NOT NULL DEFAULT 0`
2. Add a `UNIQUE` mark to `phone` in the same table
3. Append **D-64/D-65/D-66** entries to `database/consistency_report.md` — one each
   for the three added columns, since each is a separate change to the listing.
   **Check the next free number before you write it.** D-62 is A-13 (Day 5) and D-63
   is the `char(32)` UUID decision (Day 5), so D-64 is the next free slot. If your
   report already has more entries than that, continue from whatever is actually
   next — the rule is one number per change, never reuse one.
4. Re-render `eer_core.puml` with `-DPLANTUML_LIMIT_SIZE=16384`
5. Record it in the decision log in `steps/PROGRESS.md`
6. **Then** write the model

The honest framing for your report: *"Integrating with Django's authentication
framework requires three columns the UML model does not carry. They are
infrastructure, not domain — `is_staff` and `is_superuser` grant access to the admin
site, and `last_login` is session bookkeeping. The domain's own status is
`account_status`; `is_active` is derived from it."*

**Why `phone` becomes unique.** It is the login identifier — Angkas-style apps
authenticate by mobile number, and the schema's `email` is nullable so it cannot be
the username. Two users sharing a phone number would make login ambiguous. The
constraint is a strengthening, not a contradiction, but it changes the DDL and so it
gets recorded.

---

## Do this

### 1. Record the design change first (~20 min)

Do the five steps above **before** opening `models.py`. This is the discipline the
whole project rests on, and this is the first time you exercise it. If you skip it,
you have a schema document that no longer describes the database, which is worse
than either alternative.

### 2. Write the user manager (~20 min)

Create `backend/apps/accounts/managers.py`:

```python
# backend/apps/accounts/managers.py
"""Managers for the Sakay.ph account models.

The user manager exists because ``User`` uses ``phone`` as its login
identifier rather than ``username``, so Django's default
``UserManager.create_user`` signature does not apply.
"""

from django.contrib.auth.base_user import BaseUserManager

from apps.core.enums import AccountStatus, UserRole


class UserManager(BaseUserManager):
    """Manager for the USER supertype."""

    use_in_migrations = True

    def create_user(self, phone: str, password: str | None = None, **extra):
        """Create and save a user with the given phone number."""
        if not phone:
            raise ValueError("A phone number is required.")
        extra.setdefault("user_role", UserRole.PASSENGER)
        extra.setdefault("account_status", AccountStatus.ACTIVE)

        user = self.model(phone=phone.strip(), **extra)
        # set_password hashes; assigning `password` directly would store
        # plaintext and the login would silently never succeed.
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str, **extra):
        """Create a superuser for the Django admin site."""
        extra.setdefault("user_role", UserRole.ADMIN)
        extra.setdefault("account_status", AccountStatus.ACTIVE)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("full_name", "Administrator")

        if extra.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")

        return self.create_user(phone, password, **extra)
```

### 3. Write the ride-mode lookup first (~15 min)

`Vehicle.mode` points at `RIDE_MODE`, which lives in the `rides` app. If you write
`accounts/models.py` first, `makemigrations` fails with
`Related model 'rides.RideModeLookup' cannot be resolved`.

The lookup has no dependencies of its own, so write it first. Create
`backend/apps/rides/models.py`:

```python
# backend/apps/rides/models.py
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
```

`base_fare` and `per_km_rate` are `FareCalculator.baseRates` from the class diagram,
materialised as columns — which is what makes a fare change a data edit rather than a
code deploy.

Confirm it resolves:

```powershell
python manage.py check
```

Then carry on to the accounts models.

### 4. Write the six models (~90 min)

Replace `backend/apps/accounts/models.py`:

```python
# backend/apps/accounts/models.py
"""Account-domain models: USER, PASSENGER, DRIVER, VEHICLE, LGU_UNIT, ACCREDITATION.

Tables 1-6 in database/schema_listing.md.

USER uses class-table inheritance: PASSENGER and DRIVER share the supertype's
primary key rather than duplicating its columns. Django does not model
inheritance directly, so the subtype declares a OneToOneField that is also its
primary key, with db_column naming the schema's column.
"""

import uuid
from datetime import date

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.enums import AccountStatus, AccredStatus, UserRole

from .managers import UserManager

# Philippine mobile numbers, with or without the +63 country code.
PHONE_VALIDATOR = RegexValidator(
    regex=r"^(\+63|0)9\d{9}$",
    message="Enter a Philippine mobile number, e.g. 09171234567 or +639171234567.",
)


class User(AbstractBaseUser, PermissionsMixin):
    """Supertype for every person on the platform.

    Table 1. ``phone`` is the login identifier (``USERNAME_FIELD``), so it
    carries a UNIQUE constraint — see the design-change note for this step.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    full_name = models.CharField(max_length=120)
    phone = models.CharField(
        max_length=15, unique=True, validators=[PHONE_VALIDATOR]
    )
    email = models.EmailField(max_length=120, null=True, blank=True)
    # db_column keeps the schema's name. Django's own attribute is `password`.
    password = models.CharField(max_length=255, db_column="password_hash")
    registration_date = models.DateField(default=date.today)

    user_role = models.CharField(
        max_length=12, choices=UserRole.choices, default=UserRole.PASSENGER
    )
    account_status = models.CharField(
        max_length=12, choices=AccountStatus.choices, default=AccountStatus.ACTIVE
    )

    # ── Infrastructure columns added for Django's auth framework ──
    # Recorded as a design change; not part of the UML domain model.
    last_login = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]  # prompted by createsuperuser

    class Meta:
        db_table = "USER"
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-registration_date", "full_name"]
        indexes = [
            models.Index(fields=["user_role"], name="idx_user_role"),
            models.Index(fields=["account_status"], name="idx_user_status"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone})"

    # ── Properties ─────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """Django's auth backend checks this before allowing a login.

        Derived from the domain's own ``account_status`` rather than stored
        separately, so the two can never disagree.
        """
        return self.account_status == AccountStatus.ACTIVE

    @property
    def is_passenger(self) -> bool:
        return self.user_role == UserRole.PASSENGER

    @property
    def is_driver(self) -> bool:
        return self.user_role == UserRole.DRIVER

    @property
    def first_name(self) -> str:
        """Used by the admin site's header. Splits on the first space."""
        return self.full_name.split(" ")[0] if self.full_name else ""


class Passenger(models.Model):
    """Subtype of USER. Table 2.

    ``user`` is both the OneToOne link and the primary key, which is how
    class-table inheritance is expressed: PASSENGER.passenger_id is a FK to
    USER.user_id and there is no separate surrogate key.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="passenger_profile",
        db_column="passenger_id",
        limit_choices_to={"user_role": UserRole.PASSENGER},
    )

    home_address = models.CharField(max_length=255)
    gcash_number = models.CharField(max_length=15, validators=[PHONE_VALIDATOR])
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "PASSENGER"
        verbose_name = "passenger"
        verbose_name_plural = "passengers"

    def __str__(self) -> str:
        return f"Passenger: {self.user.full_name}"

    def clean(self):
        """The discriminator and the subtype must agree."""
        from django.core.exceptions import ValidationError

        if self.user_id and self.user.user_role != UserRole.PASSENGER:
            raise ValidationError(
                {"user": "A passenger profile requires user_role=PASSENGER."}
            )

    @property
    def rating_avg(self):
        """Derived — averaged from RATING, never stored.

        schema_listing.md marks this DERIVED. Returning None rather than 0
        for a passenger with no ratings keeps "unrated" distinct from "rated
        zero", which the UI needs.
        """
        from django.db.models import Avg

        from apps.rides.models import Rating

        result = Rating.objects.filter(ratee_user_id=self.user_id).aggregate(
            avg=Avg("stars")
        )["avg"]
        return round(result, 1) if result is not None else None

    @property
    def preferred_mode_names(self):
        """Resolves the multivalued attribute, ordered by preferred_rank.

        Note the name: ``preferred_modes`` is the reverse accessor Django
        creates from PASSENGER_PREFERRED_MODE (Step 05). Naming this property
        the same thing would shadow it and recurse.
        """
        return list(
            self.preferred_modes.order_by("preferred_rank").values_list(
                "mode__mode_name", flat=True
            )
        )


class Driver(models.Model):
    """Subtype of USER. Table 3."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="driver_profile",
        db_column="driver_id",
        limit_choices_to={"user_role": UserRole.DRIVER},
    )

    license_number = models.CharField(max_length=30, unique=True)
    accreditation_status = models.CharField(
        max_length=12, choices=AccredStatus.choices, default=AccredStatus.PENDING
    )
    is_online = models.BooleanField(default=False)
    # Cached aggregates — stored and refreshed, not computed on read.
    # schema_listing.md documents why: both are read on every match.
    rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True
    )
    total_trips = models.IntegerField(default=0)

    class Meta:
        db_table = "DRIVER"
        verbose_name = "driver"
        verbose_name_plural = "drivers"
        indexes = [
            # The matching engine's hot query: online, verified drivers.
            models.Index(fields=["is_online", "accreditation_status"], name="idx_driver_avail"),
        ]

    def __str__(self) -> str:
        return f"Driver: {self.user.full_name} ({self.license_number})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.user_id and self.user.user_role != UserRole.DRIVER:
            raise ValidationError(
                {"user": "A driver profile requires user_role=DRIVER."}
            )

    @property
    def is_available(self) -> bool:
        """Eligible to receive ride requests."""
        return (
            self.is_online
            and self.accreditation_status == AccredStatus.VERIFIED
            and self.user.account_status == AccountStatus.ACTIVE
        )


class LGUUnit(models.Model):
    """A city or municipal LGU that issues driver accreditation. Table 6.

    Promoted from what the class diagram carried as a bare
    ``Accreditation.issuingLGU`` string, so an LGU's name, province and
    contact details have somewhere to live.
    """

    lgu_code = models.CharField(max_length=12, primary_key=True)
    lgu_name = models.CharField(max_length=80)
    province = models.CharField(max_length=60)
    region = models.CharField(max_length=40)
    contact_no = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "LGU_UNIT"
        verbose_name = "LGU unit"
        verbose_name_plural = "LGU units"
        ordering = ["region", "province", "lgu_name"]

    def __str__(self) -> str:
        return f"{self.lgu_name}, {self.province}"


class Vehicle(models.Model):
    """A driver's registered vehicle. Table 4.

    ``driver_id`` is NOT NULL + UNIQUE: every vehicle has exactly one driver,
    and a driver has at most one vehicle (1 : 0..1 in the schema).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.OneToOneField(
        Driver, on_delete=models.CASCADE, related_name="vehicle", db_column="driver_id"
    )
    mode = models.ForeignKey(
        "rides.RideModeLookup",
        on_delete=models.PROTECT,
        related_name="vehicles",
        db_column="mode_code",
        to_field="mode_code",
    )
    plate_number = models.CharField(max_length=12, unique=True)
    model = models.CharField(max_length=60)
    capacity = models.SmallIntegerField(null=True, blank=True)
    route_info = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "VEHICLE"
        verbose_name = "vehicle"
        verbose_name_plural = "vehicles"

    def __str__(self) -> str:
        return f"{self.plate_number} ({self.model})"


class Accreditation(models.Model):
    """Sertipikadong Manong — an LGU-issued driver badge. Table 5.

    A driver has 0..* accreditations: newly registered drivers hold none yet,
    and a driver working across two cities holds two.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name="accreditations",
        db_column="driver_id",
    )
    lgu = models.ForeignKey(
        LGUUnit,
        on_delete=models.PROTECT,
        related_name="accreditations",
        db_column="lgu_code",
        to_field="lgu_code",
    )
    badge_no = models.CharField(max_length=20, unique=True)
    status = models.CharField(
        max_length=12, choices=AccredStatus.choices, default=AccredStatus.PENDING
    )
    expiry_date = models.DateField()
    badge_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "ACCREDITATION"
        verbose_name = "accreditation"
        verbose_name_plural = "accreditations"
        ordering = ["-expiry_date"]
        constraints = [
            # A driver cannot hold two badges from the same LGU.
            models.UniqueConstraint(
                fields=["driver", "lgu"], name="uq_accreditation_driver_lgu"
            ),
        ]

    def __str__(self) -> str:
        return f"Badge {self.badge_no} ({self.lgu.lgu_name})"

    @property
    def is_expired(self) -> bool:
        return self.expiry_date < timezone.localdate()

    @property
    def is_valid(self) -> bool:
        return self.status == AccredStatus.VERIFIED and not self.is_expired
```

**Three things in there deserve a second look.**

**`limit_choices_to` is not enforcement.** It only narrows the dropdown in the
admin and forms. A row with `user_role=PASSENGER` and a `Driver` profile can still be
written by raw SQL. Real enforcement is the `clean()` method plus the test in Step 09.
Do not mistake the two.

**`on_delete=PROTECT` on `Vehicle.mode` and `Accreditation.lgu`.** Deleting a ride
mode that vehicles reference would orphan them; deleting an LGU would erase the
issuer of a badge that is printed and displayed. `PROTECT` makes that a loud error.
Contrast with `CASCADE` on `Accreditation.driver` — a driver's accreditations have no
meaning without the driver.

**`Passenger.rating_avg` is a property, not a column.** The schema marks it
`DERIVED`. Computing it on read costs one aggregate query; storing it would create a
second source of truth. Note the deliberate difference from `Driver.rating`, which
*is* stored — because the schema documents it as a cached hot-path aggregate.

### 5. Set `AUTH_USER_MODEL` and the auth backend (~15 min)

Append to `backend/config/settings.py`:

```python
# ── Authentication ─────────────────────────────────────────────
# The domain's own USER table is the auth user model. This must be set
# before the first migration — changing it afterwards is a rebuild.
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]
```

**`AUTH_USER_MODEL` must be set before the first `migrate`.** If you have already
migrated, the fix is `docker compose down -v` and start again — which is cheap today
and impossible in a week. Confirm the database is still empty:

```powershell
python manage.py showmigrations
```

If `admin`, `auth` and `contenttypes` are all unapplied, you are fine.

### 6. Migrate and inspect (~30 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
python manage.py makemigrations rides accounts
python manage.py migrate
```

Then look at what Django actually built:

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW TABLES;"
```

Expected, from this step:

```
ACCREDITATION
DRIVER
LGU_UNIT
PASSENGER
USER
VEHICLE
```

Plus Django's own `auth_*`, `django_*` tables.

Confirm the inheritance is what the schema describes — `PASSENGER.passenger_id` must
be a primary key that is also a foreign key:

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW CREATE TABLE PASSENGER\G"
```

Look for `PRIMARY KEY (passenger_id)` and a `FOREIGN KEY (passenger_id) REFERENCES USER (id)`.

### 7. Prove login works (~20 min)

```powershell
python manage.py createsuperuser
```

It prompts for **Phone** and **Full name** (not username — that is the point). Then:

```powershell
python manage.py shell
```

```python
from django.contrib.auth import authenticate, get_user_model

User = get_user_model()

# 1. The model is the domain one, not Django's.
print("model:", User._meta.label)          # → accounts.User
print("table:", User._meta.db_table)       # → USER

# 2. Password hashing works.
u = User.objects.create_user(
    phone="09171234567", password="sakay-test-1234", full_name="Juan dela Cruz"
)
print("hashed:", u.password[:20])          # → pbkdf2_sha256$... (never plaintext)
print("check  :", u.check_password("sakay-test-1234"))   # → True

# 3. Authentication resolves through phone.
print("auth   :", authenticate(phone="09171234567", password="sakay-test-1234"))

# 4. The derived is_active follows account_status.
from apps.core.enums import AccountStatus
u.account_status = AccountStatus.SUSPENDED
u.save()
print("active :", u.is_active)             # → False
print("auth2  :", authenticate(phone="09171234567", password="sakay-test-1234"))  # → None

# 5. A suspended user cannot log in — that is the whole point of the derivation.
u.delete()
exit()
```

### 8. Commit (~10 min)

```powershell
Set-Location ..
git add database/ backend/apps/accounts/ backend/apps/rides/ backend/config/
git commit -m "feat(accounts): add USER, PASSENGER, DRIVER, VEHICLE, LGU_UNIT, ACCREDITATION"
git push
```

---

## Verify

```powershell
python manage.py check
python manage.py showmigrations accounts
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW TABLES;"
```

- [ ] The design change was recorded **before** the model was written
- [ ] `AUTH_USER_MODEL = "accounts.User"` is set
- [ ] `User._meta.label` is `accounts.User` and `db_table` is `USER`
- [ ] `createsuperuser` asks for **Phone**, not Username
- [ ] A created user's `password` starts with `pbkdf2_sha256$`, never plaintext
- [ ] `authenticate(phone=..., password=...)` returns the user
- [ ] Setting `account_status=SUSPENDED` makes `is_active` False and blocks login
- [ ] `SHOW CREATE TABLE PASSENGER` shows PK and FK on `passenger_id`
- [ ] `phone` has a UNIQUE index
- [ ] All six tables exist, plus `RIDE_MODE` from section 3
- [ ] `SHOW CREATE TABLE RIDE_MODE` shows `booking_fee DECIMAL(8,2) NOT NULL DEFAULT 0.00`
      — the **D-62** column, and the schema listing was updated to carry it *before*
      you wrote it
- [ ] Committed and pushed

---

## Log it

```markdown
**Step 2.03 — accounts models — DONE**

- Recorded design change: USER gains last_login, is_staff, is_superuser; phone
  becomes UNIQUE (D-64/65/66 in consistency_report.md, schema_listing.md updated,
  eer_core.puml re-rendered)
- Chose AUTH_USER_MODEL = accounts.User (option A) over a dual identity system
- USER uses phone as USERNAME_FIELD; is_active derived from account_status
- PASSENGER and DRIVER use OneToOneField(primary_key=True) for class-table inheritance
- VEHICLE 1:0..1 on driver, ACCREDITATION 1:0..* with uq_accreditation_driver_lgu
- RIDE_MODE gains booking_fee DECIMAL(8,2) DEFAULT 0 — the D-62 (A-13) column
- Verified: 6 tables created, PK/FK confirmed on PASSENGER, login and suspension work
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `AUTH_USER_MODEL refers to model 'accounts.User' that has not been installed` | `apps.accounts` not in `INSTALLED_APPS`, or `apps.py` name wrong | Check both; `name` must be `"apps.accounts"` |
| `createsuperuser` asks for a username | `AUTH_USER_MODEL` not set, so Django used `auth.User` | Set it, then `docker compose down -v` and re-migrate |
| `Cannot change AUTH_USER_MODEL` / migration conflicts | You migrated with the default user model first | `docker compose down -v`, delete `apps/*/migrations/0*.py`, migrate fresh |
| `Field 'password_hash' has no default` | `db_column` set but `max_length` mismatched the schema | `max_length=255`, matching `VARCHAR(255)` |
| `ValueError: Related model 'rides.RideModeLookup' cannot be resolved` | Section 3 was skipped, so `rides/models.py` has no `RideModeLookup` | Write section 3 first — the lookup has no dependencies and must exist before `Vehicle` |
| `ValidationError: A passenger profile requires user_role=PASSENGER` | `clean()` doing its job | Set the user's `user_role` before creating the profile |
| `clean()` never fires | `clean()` is only called by `full_clean()`, not `save()` | Known Django behaviour — Step 09 tests it explicitly, and Phase 3's serializers call it |
| `is_active` cannot be assigned | It is a read-only property | Set `account_status` instead. That is the design |
| Two users with the same phone were allowed | The unique constraint did not apply | Check `SHOW CREATE TABLE USER` for `UNIQUE KEY` on `phone` |

---

## After this step

The people exist. Next come the rides themselves — including `RIDE_LEG`, the weak
entity whose composite primary key Django cannot express directly.

Next: [04 — Models: rides core](04-models-rides-core.md)
