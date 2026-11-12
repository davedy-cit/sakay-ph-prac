# Phase 2 — Database and Domain Model

**Days 8–14 · 13–19 November 2026**
**Time budget: 7 days — the largest phase in the project**

---

## Goal

The 27-table schema in `database/schema_listing.md` exists as real, migrated MySQL
tables with real constraints, seeded with the lookup data the app needs, and covered
by model tests. Nothing else.

---

## Why this phase is big

Phase 1 was 1.5 days and produced no application code. Phase 2 is 7 days and
produces no *features*. That is not a scheduling mistake.

The schema is the one part of the project where a mistake is expensive. A wrong
column name in a Vue component costs ten minutes. A wrong cardinality in `RIDE`
costs a migration, a data backfill, and every serializer and query written against
it. You have 27 tables with 4 composite primary keys, class-table inheritance, a
weak entity and a unary relationship. Getting them right once is faster than
getting them wrong and fixing them for three weeks.

The design is already done and already audited — `consistency_report.md` records 61
defects found and fixed on paper. **This phase is translation, not design.** If you
find yourself redesigning a table, stop and check whether the design is actually
wrong or you are just second-guessing it.

---

## The rule for this phase

> The code follows the design. Never the reverse.

Every column you write should be traceable to a row in `schema_listing.md`. If you
need a column that is not there, the procedure is:

1. Change `schema_listing.md` first
2. Append the change to `database/consistency_report.md` as a new entry
3. Re-render the affected EER diagram
4. Record it in the decision log in `steps/PROGRESS.md`
5. **Then** write the column

That is `CONTRIBUTING.md`'s design-change procedure, and this phase is where it
earns its place. One change has already been through it — see "The one design change
already decided" below.

---

## Steps

| | Step | Day | What exists when it's done |
|---|---|---|---|
| ⬜ | [01 — Apps and shared conventions](01-apps-and-shared-conventions.md) | 8 | Five Django apps; every domain enum as a `TextChoices`; the UUID-PK and timestamp conventions every model follows; `PLATFORM_CONFIG` (table 27, D-62) |
| ⬜ | [02 — Settings, environment and database connection](02-settings-env-and-docker.md) | 9 | `settings.py` reads `.env`; Django connects to MySQL 8.4 and answers `SELECT 1` |
| ⬜ | [03 — Models: accounts](03-models-accounts.md) | 10 | USER, PASSENGER, DRIVER, VEHICLE, LGU_UNIT, ACCREDITATION — tables 1–6 — plus RIDE_MODE (table 7, written first so `Vehicle.mode` resolves) |
| ⬜ | [04 — Models: rides core](04-models-rides-core.md) | 11 | LOCATION, RIDE, RIDE_LEG — tables 10–12, including the weak entity. (`RIDE_MODE` already landed in Step 03) |
| ⬜ | [05 — Models: rides features](05-models-rides-features.md) | 12 | SURGE_PERIOD, PAKYAWAN_GROUP, PASSENGER_PREFERRED_MODE, TRIP_TRACKING, CANCELLATION, RATING — tables 8, 13, 23–26 |
| ⬜ | [06 — Models: payments](06-models-payments.md) | 13 | PAYMENT_METHOD, WALLET, WALLET_TXN, PAYMENT, FARE_SHARE, RECEIPT, DRIVER_PAYOUT — tables 9, 14–19 |
| ⬜ | [07 — Models: safety](07-models-safety.md) | 13 | SOS_ALERT, TRUSTED_CONTACT, SOS_NOTIFICATION — tables 20–22 |
| ⬜ | [08 — Migrations, seed data and admin](08-migrations-seed-and-admin.md) | 14 | All 27 tables migrated; lookup tables seeded; every model visible in the Django admin |
| ⬜ | [09 — Model tests](09-model-tests.md) | 14 | pytest runs; the constraints that matter are asserted, not assumed |

**Days 13 and 14 carry two steps each.** That is deliberate — by then the model
writing is mechanical and the two heaviest steps (03 and 04) are behind you. If you
fall behind, the ladder in `docs/plan/02-roadmap.md` says what to cut, and it is
never the tests.

---

## The one design change already decided

Audit finding **A-13** found pricing behaviours visible in the mockups that have no
schema home: a ₱3.00 booking fee, a commission waiver on the first five trips, and a
chain-leg discount. It also found that `mock3`'s fare arithmetic does not close —
`₱144.00 − ₱96.00 + ₱3.00` is printed as `₱48.00` when it is `₱51.00`.

**This was decided on 11 November 2026 and recorded as D-62.** The four actions
below are what D-62 says, and they are no longer a recommendation you may take or
leave — they are the design:

| # | Action | Lands in |
|---|---|---|
| 1 | Add `RIDE_MODE.booking_fee DECIMAL(8,2) NOT NULL DEFAULT 0` | [Step 03](03-models-accounts.md) §3 |
| 2 | Put the commission rate in a `PLATFORM_CONFIG` key-value table | [Step 01](01-apps-and-shared-conventions.md) §6 |
| 3 | **Drop** the chain-leg discount — no rule justifies it | nothing to build |
| 4 | Fix the mockup arithmetic (`mock3`: ₱48.00 → ₱51.00) | already corrected in `consistency_report.md` §3.10 |

The two code changes land in this phase:

- `booking_fee` is added to `RideModeLookup` in [Step 03](03-models-accounts.md)
- `PLATFORM_CONFIG` is added in [Step 01](01-apps-and-shared-conventions.md) as a
  model in the `core` app — `core` already exists, and it is where cross-cutting
  tables belong
- Both are covered by the **D-62** entry recorded in Step 0.01 — mark that entry
  `implemented (Phase 2)` and add the corresponding rows to `schema_listing.md`,
  **before** the migration runs

**Numbering:** A-13 is **D-62**. Do not issue a second entry for it in this phase.
Phase 2's own design changes continue from **D-64** (D-63 is taken by the `char(32)`
UUID decision in Step 0.03). See the "Design-change numbers" section below.

What you must not do is add either column silently. If you disagree with D-62, the
route is a *new* D-number that supersedes it — not a quiet divergence from it.

---

## Design-change numbers

`consistency_report.md` uses one number per design change, and the numbering is
shared across phases. Two were already spent before this phase started, so the
Phase 2 steps must not reissue them:

| # | Change | Where decided |
|---|---|---|
| … | D-01 … D-61 — the original audit's defect register | Phase 0, pre-existing |
| **D-62** | A-13 — booking fee, commission rule, chain discount dropped, `mock3` arithmetic corrected | Day 5, [Step 0.01](../phase-0-design-completion/01-complete-technology-stack.md) |
| **D-63** | UUIDs stored as `char(32)` on MySQL rather than a native `UUID` column | Day 5, [Step 0.03](../phase-0-design-completion/03-design-freeze-check.md) |
| **D-64/65/66** | `USER` gains `last_login`, `is_staff`, `is_superuser`; `phone` becomes `UNIQUE` | Phase 2, [Step 03](03-models-accounts.md) |
| **D-67** | The four composite primary keys become surrogate `id` + `UniqueConstraint` | Phase 2, [Step 04](04-models-rides-core.md) |

**Before writing any entry, open `consistency_report.md` and read the last number in
it.** The table above is what the step files expect; your report is what actually
happened. If they disagree, the report wins and you renumber forward from it —
what you never do is reuse a number, because two different changes sharing one ID
destroys the audit trail the report exists to provide.

---

## The four composite primary keys

These are the part of the schema most likely to go wrong in Django, because Django
does not support composite primary keys. Every one of them needs a documented
workaround, and the workaround is `UniqueConstraint` — a unique index that the
database enforces even though Django's ORM will not treat it as a primary key.

| Table | Documented PK | Django approach |
|---|---|---|
| RIDE_LEG | `(ride_id, leg_no)` | surrogate `id` + `UniqueConstraint(fields=["ride", "leg_no"])` |
| FARE_SHARE | `(payment_id, passenger_id)` | surrogate `id` + `UniqueConstraint(fields=["payment", "passenger"])` |
| SOS_NOTIFICATION | `(alert_id, contact_id)` | surrogate `id` + `UniqueConstraint(fields=["alert", "contact"])` |
| PASSENGER_PREFERRED_MODE | `(passenger_id, mode_code)` | surrogate `id` + `UniqueConstraint(fields=["passenger", "mode"])` |

**Why this is acceptable and how to defend it.** The constraint is enforced by MySQL,
which is what matters for integrity. The surrogate key is an implementation detail
Django requires. Record the substitution in `consistency_report.md` as a documented
deviation — an assessor who notices it should find your explanation, not a silence.

The alternative — `django-composite-pk` or a raw-SQL migration — adds a dependency
or hand-written DDL for no gain in a project this size.

---

## Conventions every model in this phase follows

These are decided in [Step 01](01-apps-and-shared-conventions.md) and applied without
exception afterwards. They exist so that Step 04 looks like Step 06.

| Convention | Rule | Why |
|---|---|---|
| **Primary key** | `UUIDField(primary_key=True, default=uuid4, editable=False)` named `<entity>_id` | Matches the schema exactly; UUIDs are not guessable, which matters for a ride-tracking app |
| **UUID storage** | `CharField(max_length=32)` via a custom field, or MySQL `CHAR(32)` | See "If it goes wrong" — the default `CHAR(32)` choice has a performance cost that is irrelevant here but worth knowing |
| **Timestamps** | `DateTimeField`; `auto_now_add` only where the schema says *(added)* | `request_time` is a business timestamp, not an audit one |
| **Money** | `DecimalField(max_digits=..., decimal_places=2)` | **Never `FloatField`.** A fare that rounds wrong is a bug you cannot explain |
| **Coordinates** | `DecimalField(max_digits=9, decimal_places=6)` | Matches the schema; ~11 cm precision, more than enough |
| **Enums** | `TextChoices` class, `max_length` matching the schema's VARCHAR | The schema stores short VARCHAR codes so new values need no migration |
| **Table names** | `Meta.db_table` set explicitly to the schema's UPPER_SNAKE name | Keeps the database readable next to the diagrams |
| **Related names** | Explicit `related_name` on every FK | Django's default `ride_set` is useless in a query |
| **Nullability** | Match the schema exactly, including `null=True` on FKs | Every nullable FK in this schema is nullable for a documented reason |

---

## Milestone M2 exit criterion

> `python manage.py migrate` on a fresh database creates all 27 tables, and
> `pytest` passes.

Two commands, no manual steps, no "first run this SQL". If an assessor has to read
your notes to get the database up, M2 is not met.

Verify it the hard way — the way an assessor would:

```powershell
docker compose down -v
docker compose up -d
Set-Location backend
python manage.py migrate
python manage.py seed_lookups
pytest
```

---

## What this phase deliberately does not do

| Not done here | Done in |
|---|---|
| Serializers, viewsets, URLs | Phase 3 |
| JWT authentication and permissions | Phase 3 |
| Fare calculation logic, matching engine | Phase 3 |
| WebSocket consumers | Phase 3 |
| Any Vue code | Phase 4 |
| The `simulate_driver` command | Phase 3 |

Phase 2 produces a database and a model layer. Resist the pull to start on the API —
a serializer written before its models are migrated is a serializer you rewrite.

---

## Watch out for

**Do not run `makemigrations` after every model.** Write the whole app's models,
then migrate once. Forty small migrations make the history unreadable and are much
harder to squash later than to avoid now.

**Do not edit a migration by hand.** If a migration is wrong, fix the model and
generate a new one. Hand-edited migrations are how a schema drifts from its models.

**Do not skip Step 09.** The tests in this phase are cheap and they catch the
constraint mistakes that are otherwise invisible until Phase 3's API returns wrong
data. `consistency_report.md` documents the design; the tests prove the
implementation matches it.

**Do not add a table the design does not have.** If you feel the need for one, that
is a design change, and the procedure is above.

---

## Next

**Phase 3 — Backend API** · Days 15–22 · [../phase-3-backend-api/00-overview.md](../phase-3-backend-api/00-overview.md)
