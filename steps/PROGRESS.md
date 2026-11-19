# Sakay.ph — Progress Log

**Project:** Sakay.ph — Isang App, Lahat ng Sakyan
**Subject:** CCS670 Object-Oriented Software Development
**Window:** 6 November 2026 → 6 December 2026 (31 days)
**Today:** 15 November 2026 — calendar **Day 10**. Steps 02.01 and 02.02 are done, so the
ladder stands at **one day** behind: Step 02.03 is Day 10's own step, and starting it today
is what closes the gap

> **This is a living document.** Update it at the end of every working session —
> it takes five minutes and it is the evidence that you followed a process, which
> is what CCS670 actually assesses. An empty log at submission is worth less than
> an honest one with a few missed days in it.

**Markers:** `[ ]` not started · `[~]` in progress · `[x]` done and verified · `[!]` blocked · `[-]` skipped deliberately

> ### Where I am right now
>
> **Next action:** **Step 2.03** — the account models: `USER`, `PASSENGER`, `DRIVER`,
> `VEHICLE`, `LGU_UNIT`, `ACCREDITATION`, plus `RIDE_MODE` written first so `Vehicle.mode`
> resolves ([03 — Models: accounts](phase-2-database/03-models-accounts.md)).
> Nothing is uncommitted: Steps 1.06, 2.01 and 2.02 are all committed and pushed.
>
> **Pushed 15 Nov** — the three-commit backlog split kept the design commit an ancestor of
> the code commit, so the artefacts still precede the code in history:
>
> | Commit | What it carries |
> |---|---|
> | `9e59550` | `chore(repo)` — docker services, tooling, frontend scaffold, install log |
> | `2e6f216` | `docs(design)` — D-62 across the artefacts, **D-64** recorded, both EER PNGs re-rendered |
> | `d13d34b` | `feat(repo)` — the Django backend: five apps, 13 enums, shared conventions |
> | `d137254` | `feat(config)` — `settings.py` wired to `.env`, MySQL 8.4, Redis, DRF and Channels |
>
> **Step 2.01's artefact-first requirement is now met.** Table 27 (`PLATFORM_CONFIG`) and
> `RIDE_MODE.booking_fee` are in `database/schema_listing.md`, the `⚠ Pending` callout is
> resolved, both EER sources carry them, and D-62's status in `consistency_report.md` §3.10
> is `implemented (Phase 2)`. The `RIDE_MODE.booking_fee` **model column** is Step 02.03's;
> its **value** — ₱3.00 flat, charged once per ride — is **D-64**, decided 14 Nov (§3.12).
>
> **Verified state of the repository (checked 15 Nov):**
>
> | Check | Actual |
> |---|---|
> | `technology_stack.md` | ✅ **complete** — §1–§7; §7 now carries the real pin-vs-resolved evidence table, and the ten `pin at install` cells in §2 are filled |
> | `consistency_report.md` | ✅ D-01…D-61 fixed, plus **D-62** (A-13), **D-63** (UUID storage) and **D-64** (the booking fee's value, §3.12) |
> | D-62 propagation | ✅ done — 27 tables in every forward-looking document; historical rows left at 26 on purpose; the wrong `Step 02.04` cross-reference corrected to `02.03` |
> | `schema_listing.md` | ✅ **27 tables** — table 27 (`PLATFORM_CONFIG`) and `RIDE_MODE.booking_fee` added in Step 02.01; the `⚠ Pending` callout is resolved. The `CHAR(32)` UUID note (D-63) stands |
> | `database/diagrams/*.puml` | ✅ **carry D-62** — `eer_development.puml` is now 27 entities and `eer_core.puml` 13, both with `PLATFORM_CONFIG` and `RIDE_MODE.booking_fee` |
> | `database/diagrams/*.png` | ✅ **re-rendered 14 Nov** — `eer_development.png` **3805×3063** (27 entities) and `eer_core.png` **2356×2557** (13 entities) now carry `PLATFORM_CONFIG` and `RIDE_MODE.booking_fee`, confirmed by opening the rendered PNGs, not inferred. Neither dimension touches the 4096 clip (D-61). `eer_features.png` and `er_overview.png` correctly untouched — `eer_features.puml` is unchanged by D-62 and `er_overview.puml` does not model `RIDE_MODE`. Rendered via Docker `plantuml/plantuml:1.2026.10` (bundles Graphviz): `--entrypoint java … -DPLANTUML_LIMIT_SIZE=16384 -jar /opt/plantuml.jar -tpng -charset UTF-8` |
> | Root `README.md` | ✅ **written** — Step 0.02 |
> | `docs/plan/design-freeze.md` | ✅ **written** — Step 0.03; 13 limitations, 3 open questions; commit column filled 13 Nov |
> | Git repository | ✅ **live** — `davedy-cit/sakay-ph-prac`, branch `main`, pushed |
> | `CONTRIBUTING.md` | ✅ **written** — Step 1.05, commit `cfa6e7f` |
> | `docker-compose.yml` | ✅ **written and validated** — `docker compose config --quiet` passes; MySQL 8.4 + Redis 7-alpine, healthchecks, named volumes, `utf8mb4` |
> | `requirements/base.txt`, `requirements/dev.txt` | ✅ **written** — 17 exact pins; every one resolved to exactly the pinned version |
> | `.venv/` | ✅ **created** — Python 3.14.9, 56 packages, pip upgraded to 26.3, no compiler invoked |
> | `backend/` | ✅ **scaffolded** — Django 6.1.3 + DRF; `config/__init__.py` registers the PyMySQL shim; `manage.py check` → 0 issues; `runserver` returns HTTP 200 |
> | `frontend/` | ✅ **scaffolded** — Vue 3.5.45 + Vite 8.3.8 + Tailwind 4.3.5; 380 packages; dev server returns HTTP 200 |
> | `backend/config/settings.py` | ✅ **Step 2.02 complete** — every secret read from the root `.env` through django-environ; MySQL 8.4.13 on host port 3307; utf8mb4 proven on connection, server and collation with the round-trip returning **MATCH**; Redis proven on **db 1** (cache) and **db 0** (channel layer); `check` → 0 issues. Commit `d137254` |
> | `.env` | ✅ **present and ignored** — `git check-ignore -v .env` resolves to `.gitignore:5`; no secret is in the tree |
> | `backend/apps/` | ✅ **Step 2.01 complete** — five apps with dotted `apps.py` names, all 13 enums in `core/enums.py`, the abstract models, and `PlatformConfig`; `manage.py check` → 0 issues. Created ahead of schedule, and its artefact-first requirement is now met |
> | `docs/plan/install-log.txt` | ✅ **complete** — toolchain, backend and frontend install proof, services proof, and the 5 recorded deviations, above the raw pip output |
> | Docker Desktop | ✅ **installed and running** — server 29.9.3, Compose v5.7.0, WSL 2 kernel 6.18.58.1 |
> | Docker MySQL host port | **3307** — a native `MySQL84` service owns 3306, so `docker-compose.yml` maps `3307:3306` |
> | Vite dev server | reachable at **`http://localhost:5173`** — it binds IPv6 loopback only, so `127.0.0.1:5173` does not answer |
>
> **Phase 0 complete. Phase 1 complete. Steps 2.01 and 2.02 complete — all pushed.**
> The plan is **one day** behind the calendar — M2 still has five days for Steps
> 02.03–02.09, which is workable because Phase 2 is translation rather than design.
> Django can now talk to MySQL and Redis; there are still no application tables.

---

## 1. Master tracker

### Phase 0 — Design completion · Days 1–5 · 6–10 Nov

| | Step | Day | Status |
|---|---|---|---|
| ✅ | [00 — Phase overview](phase-0-design-completion/00-overview.md) | 5 | `[x]` |
| ✅ | [01 — Complete the technology stack document](phase-0-design-completion/01-complete-technology-stack.md) | 5 | `[x]` |
| ✅ | [02 — Write the root README](phase-0-design-completion/02-root-readme.md) | 5 | `[x]` |
| ✅ | [03 — Design freeze check](phase-0-design-completion/03-design-freeze-check.md) | 5 | `[x]` |

**Phase 0 complete 11 Nov.** The design is frozen at
[`docs/plan/design-freeze.md`](../docs/plan/design-freeze.md). Its commit column is filled on 13 Nov — every artefact points at the commit that introduced it.

**Milestone M1 exit criterion (shared with Phase 1):** a stranger can clone the repo,
read the README, and understand the project without asking you anything. The README is
written; the *clone* half needs Phase 1.

### Day 6 — Wed 11 Nov (executed 13 Nov)

**Steps 1.01–1.04 — repository created and pushed — DONE**

- `git init` on `main`; `backend/`, `frontend/`, `tools/` created with `.gitkeep`
- `.gitignore` written **before** any `.env` existed; `git check-ignore -v .env`
  confirms `.gitignore:5:.env` matches. `.env` has never been tracked
- GitHub repo `sakay-ph-prac` created; remote `origin` added
- Design phase pushed as 8 focused commits, not one blob:
  `f7fe035` repo · `38bd60e` proposal+stack · `03f344f` UML · `2ecf717` database ·
  `32817d4` mockups · `868e43b` plan+review+steps · `9452a22` README ·
  `14812c1` build folders + editor settings
- Freeze commit column filled — each of the 14 artefacts points at its introducing commit
- **First commit:** `f7fe035` · **Head:** `14812c1`

### Day 7 — Thu 12 Nov (executed 13 Nov)

**Step 1.06 — Scaffold Django and Vue, prove the environment — DONE**

*Backend*

- `.venv` created on Python 3.14.9; pip upgraded 26.2.2 → 26.3
- `requirements/base.txt` (14 pins) and `requirements/dev.txt` (5 pins) written, each pin
  carrying a comment explaining the choice
- `pip install -r requirements/dev.txt` → **56 packages, exit 0, no compiler invoked.**
  Every direct pin resolved to exactly the version pinned
- `cryptography` 50.0.2 arrived as a prebuilt `cp311-abi3` wheel — the Rust-toolchain risk
  this plan flagged for Python 3.14 did not materialise
- `backend/config/__init__.py` registers `pymysql.install_as_MySQLdb()`, so PyMySQL is a
  drop-in for `mysqlclient` with no C toolchain on Windows
- `python manage.py check` → **0 issues**; `runserver` → HTTP 200

*Frontend*

- `create-vue` scaffold: Vue 3.5.45, Vite 8.3.8, Vue Router 5.5.0, Pinia 4.1.0
- `npm install` 337 · `+ axios leaflet` 26 · `+ tailwindcss @tailwindcss/vite` 17 → **380**
- **Vue Router 5 and Pinia 4 both exist.** The doubt recorded in stack doc §7 — that the
  pins might name majors that do not exist — is settled in the project's favour
- Dev server → HTTP 200 at `http://localhost:5173`

*Services*

- `docker-compose.yml` written and validated (`docker compose config --quiet` passes)
- MySQL 8.4 and Redis 7-alpine both healthy; `character_set_server` = `utf8mb4`,
  `collation_server` = `utf8mb4_unicode_ci`, `redis-cli ping` → `PONG`
- Django and Vite confirmed listening **at the same moment**, not one after the other

*Defect found and fixed*

- A `$` in `MYSQL_PASSWORD` made Docker Compose interpolate it to an empty string while
  django-environ read the file literally, so the container and the app held **different**
  passwords. It surfaced as `ERROR 1045 (28000): Access denied for user
  'sakayph'@'localhost'` — an error that points at the app, not at the password.
  **Proven before fixing:** 50 characters in `.env`, 47 passed by Compose
- Fixed by regenerating the password as 32 alphanumerics, then `docker compose down -v`
  followed by `up -d`. The `down -v` is required: the MySQL entrypoint issues `CREATE USER`
  only when the data directory is empty, so editing `.env` alone leaves the old password in
  place and makes the fix look ineffective. Verified afterwards: `identical: True`, app user
  connects
- Documented in `.env.example` and in the Step 1.02 troubleshooting table

*Documentation*

- `technology_stack.md` §3 updated with the real Docker / Compose / pip versions, and the
  "Two honest gaps" prose replaced — there are no gaps now
- `technology_stack.md` §7 replaced its stub with the pin-versus-resolved evidence table for
  all 56 backend and 15 frontend packages; §2's ten `pin at install` cells filled
- `docs/plan/install-log.txt` gained a toolchain, install-proof, services-proof and
  deviations header above the raw pip output

**Commit:** `9e59550` (tooling and scaffold) and `d13d34b` (the backend) — pushed 15 Nov
with the Step 2.01 work, once the backlog was split into three commits

---

### Day 8 — Fri 13 Nov (executed 13–14 Nov)

**Step 2.01 — apps and shared conventions — DONE**

- Created `backend/apps/` with `core`, `accounts`, `rides`, `payments`, `safety`; every
  `apps.py` carries the dotted `name = "apps.<app>"`, not the bare app name — the single
  most common failure in the step, avoided by checking all five
- All **13 domain enums** written once in `apps/core/enums.py` as `TextChoices`, stored as
  short VARCHAR codes rather than MySQL `ENUM`, so a new ride mode needs no migration
- Shared abstractions in `apps/core/models.py`: `UUIDModel`, `TimeStampedModel`,
  `MoneyField` (so no model can reach for `FloatField` by accident) and `CoordinateField`
  (`DECIMAL(9,6)`)
- `apps/core/constants.py` holds only structural values; anything an operator would change
  belongs in `PLATFORM_CONFIG` instead
- **Decision:** the PK attribute is named `id` (the Django idiom) while `db_table` keeps
  the schema's `UPPER_SNAKE` name, so the database still reads like the diagrams
- Added `PlatformConfig` — **table 27**, the D-62 key-value table — and marked D-62's
  status in `consistency_report.md` §3.10 `implemented (Phase 2)`
- `python manage.py check` → **0 issues**

*The artefact-first requirement, completed 14 Nov*

- Step 2.01 originally said "schema listing and consistency report" and never mentioned
  the diagrams, so the first run left `eer_development.png` showing **26** entities while
  the listing said 27 — and `schema_listing.md`'s header asserts every table appears in
  the diagram, which made that header false. Found on 14 Nov not by reading but by
  **opening the PNG**
- Both EER sources gained `PLATFORM_CONFIG` and `RIDE_MODE.booking_fee`; both PNGs were
  re-rendered with the pinned `plantuml/plantuml:1.2026.10` image (it bundles Graphviz;
  no jar lives in the repo and `dot` is not on `PATH`), with `-DPLANTUML_LIMIT_SIZE=16384`
  and `-charset UTF-8`. `eer_development.png` 3504×3332 → **3805×3063** (27 entities),
  `eer_core.png` 2065×2773 → **2356×2557** (13)
- Verified by opening the renders, **not** by the exit code — a clipped render still
  writes a PNG and exits 0 (D-61)
- The step file now carries the instruction it should always have had, and
  `CONTRIBUTING.md` records the render recipe so the next diagram change has one

**Commit:** `2e6f216` (the design artefacts, including both PNGs) and `d13d34b` (the
backend) — pushed 15 Nov, after the two-day backlog was split into three commits so the
design commit is an ancestor of the code commit

---

### Day 9 — Sat 14 Nov (executed 15 Nov)

**Step 2.02 — settings, environment and database connection — DONE**

- `settings.py` reads every secret and every environment-specific value from the
  repository-root `.env` through django-environ, so nothing in the file changes between
  this machine and the submission build. `config/__init__.py` still carries the PyMySQL
  shim from Step 1.06 — the one thing that keeps `Error loading MySQLdb module` away
- MySQL 8.4 connection proven: `connection.vendor` → `mysql` and
  `connection.mysql_version` → `(8, 4, 13)`, on **port 3307** — the compose mapping,
  because a native `MySQL84` service owns 3306 on this machine
- **The encoding test, which is the one that actually matters.** `character_set_client`,
  `_connection`, `_results` and `_server` are all `utf8mb4`, and `collation_server` is
  `utf8mb4_unicode_ci`. `Barangay Peñaflor ₱25.00 🚐🛺` round-tripped through a temporary
  `utf8mb4` table with identical codepoints (`0xf1`, `0x20b1`, `0x1f690`, `0x1f6fa`) and
  27 of 27 characters — **MATCH**. `character_set_system` reads `utf8mb3`, which is MySQL's
  own metadata charset and not something the app can or needs to change
- Redis proven on **both** paths: `cache.get("probe")` → `kumusta`, with the raw key
  `sakayph:1:probe` visible in **db 1**, and the channel-layer `send` completing without
  error against **db 0**. The split is D-11's, so a cache flush cannot drop a live
  WebSocket group
- Two `DATABASES["default"]["OPTIONS"]` keys are load-bearing and both are in: `charset:
  utf8mb4` — the *connection* charset, which is separate from the server's — and
  `init_command: SET sql_mode='STRICT_TRANS_TABLES'`, without which MySQL truncates an
  over-long value with a warning instead of raising, which is a silent data-loss bug
- **The §6 test was run as a script, not pasted into `manage.py shell`.** The interactive
  console needs a blank line to close a block, so a multi-line paste raises
  `IndentationError` on every line after the first — exactly what the first attempt did.
  `manage.py shell -c "exec(open(...).read())"` runs the same code without the console
  parsing it line by line
- `.env` confirmed still ignored: `git check-ignore -v .env` resolves to `.gitignore:5`
- `python manage.py check` → **0 issues**. `migrate` deliberately not run — there are no
  application models yet, so it would only create Django's own tables

*Also decided on 14 Nov, while Step 02.01's artefacts were being finished:* the booking
fee's **value**. D-62 created `RIDE_MODE.booking_fee` and left it open; it is now **₱3.00
flat on all six modes, charged once per ride** — recorded as **D-64** in
`consistency_report.md` §3.12 and as **D-18** in the decision log. The seed lands in
Step 02.08; the arithmetic is Phase 3's.

**Commit:** `d137254`

---

### Phase 1 — Repository · Days 6–7 · 11–12 Nov

| | Step | Day | Status |
|---|---|---|---|
| ✅ | [00 — Phase overview](phase-1-repository/00-overview.md) | 6 | `[x]` |
| ✅ | [01 — Initialise git and the folder structure](phase-1-repository/01-git-init-and-structure.md) | 6 | `[x]` |
| ✅ | [02 — Write `.gitignore` and `.env.example`](phase-1-repository/02-gitignore-and-env-example.md) | 6 | `[x]` |
| ✅ | [03 — Create the GitHub repository](phase-1-repository/03-github-repo.md) | 6 | `[x]` |
| ✅ | [04 — First push](phase-1-repository/04-first-push.md) | 6 | `[x]` |
| ✅ | [05 — Workflow conventions](phase-1-repository/05-workflow-conventions.md) | 7 | `[x]` |
| ✅ | [06 — Scaffold Django and Vue, prove the environment](phase-1-repository/06-scaffold-and-verify.md) | 7 | `[x]` |

---

### Phase 2 — Database · Days 8–14 · 13–19 Nov

| | Step | Day | Status |
|---|---|---|---|
| ⬜ | [00 — Phase overview](phase-2-database/00-overview.md) | 8 | `[ ]` |
| ✅ | [01 — Apps and shared conventions](phase-2-database/01-apps-and-shared-conventions.md) | 8 | `[x]` |
| ✅ | [02 — Settings, `.env`, and Docker services](phase-2-database/02-settings-env-and-docker.md) | 9 | `[x]` |
| ⬜ | [03 — Models: `USER`, `PASSENGER`, `DRIVER`, `VEHICLE`, `LGU_UNIT`, `ACCREDITATION`](phase-2-database/03-models-accounts.md) | 10 | `[ ]` |
| ⬜ | [04 — Models: `LOCATION`, `RIDE`, `RIDE_LEG`](phase-2-database/04-models-rides-core.md) | 11 | `[ ]` |
| ⬜ | [05 — Models: surge, Pakyawan, tracking, cancellation, rating](phase-2-database/05-models-rides-features.md) | 12 | `[ ]` |
| ⬜ | [06 — Models: payment, wallet, receipt, payout](phase-2-database/06-models-payments.md) | 13 | `[ ]` |
| ⬜ | [07 — Models: SOS alert, trusted contacts, notifications](phase-2-database/07-models-safety.md) | 13 | `[ ]` |
| ⬜ | [08 — Migrations, admin, seed](phase-2-database/08-migrations-seed-and-admin.md) | 14 | `[ ]` |
| ⬜ | [09 — Model tests](phase-2-database/09-model-tests.md) | 14 | `[ ]` |

**Milestone M2 exit criterion:** `migrate` runs clean against an **empty volume**
(`docker compose down -v` first); `manage.py seed_lookups` is idempotent — running it
twice changes nothing; all 27 models appear in the admin; the model tests and the
schema-contract test pass.

---

### Phase 3 — Backend API · Days 15–22 · 20–27 Nov

Full step breakdown: [phase-3-backend-api/00-overview.md](phase-3-backend-api/00-overview.md)

| | Step | Day | Status |
|---|---|---|---|
| ⬜ | 01 — JWT auth, registration, simulated OTP | 15 | `[ ]` |
| ⬜ | 02 — Serializers, viewsets, OpenAPI schema | 16 | `[ ]` |
| ⬜ | 03 — `FareCalculator` + unit tests | 17 | `[ ]` |
| ⬜ | 04 — `MatchingEngine`, accept/decline, timeout | 18 | `[ ]` |
| ⬜ | 05 — Ride lifecycle + cancellation policy | 19 | `[ ]` |
| ⬜ | 06 — Isang Biyahe trip chain | 20 | `[ ]` |
| ⬜ | 07 — Pakyawan grouping + fare split | 20 | `[ ]` |
| ⬜ | 08 — Channels tracking + `simulate_driver` | 21 | `[ ]` |
| ⬜ | 09 — SOS Bantay | 21 | `[ ]` |
| ⬜ | 10 — Bagyo Mode | 21 | `[ ]` |
| ⬜ | 11 — Payment, wallet, receipt | 22 | `[ ]` |
| ⬜ | 12 — Driver payout | 22 | `[ ]` |

> The twelve step files are written around Day 14, once Phase 2 has settled. The
> numbers above are the filenames they will get — `phase-3-backend-api/NN-name.md`.

**Milestone M3 exit criterion:** Swagger UI at `/api/docs/` can drive a complete
ride — book → match → chain → split → track → SOS → surge → pay → receipt →
payout → rate — with no frontend involved.
**🚩 FEATURE FREEZE end of Day 22.**

---

### Phase 4 — Frontend · Days 23–27 · 28 Nov – 2 Dec

Full step breakdown: [phase-4-frontend/00-overview.md](phase-4-frontend/00-overview.md)

| | Step | Day | Status |
|---|---|---|---|
| ⬜ | 01 — Vue scaffold, Tailwind tokens, routing | 23 | `[ ]` |
| ⬜ | 02 — Auth screens | 24 | `[ ]` |
| ⬜ | 03 — Shared components and design tokens | 24 | `[ ]` |
| ⬜ | 04 — API client and stores | 24 | `[ ]` |
| ⬜ | 05 — Home / booking screen (`mock1`) | 24 | `[ ]` |
| ⬜ | 06 — Tracking screen (`mock2`) | 25 | `[ ]` |
| ⬜ | 07 — Payment / receipt screen (`mock3`) | 26 | `[ ]` |
| ⬜ | 08 — Driver screen (`mock4`) | 27 | `[ ]` |

**Milestone M4 exit criterion:** all four mockup screens live in the browser,
driven by real API calls, with the vehicle moving on the map.
**🚩 UI FREEZE end of Day 27.**

---

### Phase 5 — Integration & testing · Day 28 · 3 Dec

Full step breakdown: [phase-5-integration-testing/00-overview.md](phase-5-integration-testing/00-overview.md)

| | Step | Day | Status |
|---|---|---|---|
| ⬜ | 01 — End-to-end scenarios (one per feature) | 28 | `[ ]` |
| ⬜ | 02 — Persona UAT scripts | 28 | `[ ]` |
| ⬜ | 03 — Bug fixing and regression | 28 | `[ ]` |

---

### Phase 6 — Documentation & submission · Days 29–31 · 4–6 Dec

Full step breakdown: [phase-6-documentation-submission/00-overview.md](phase-6-documentation-submission/00-overview.md)

| | Step | Day | Status |
|---|---|---|---|
| ⬜ | 01 — Final report and traceability matrix | 29 | `[ ]` |
| ⬜ | 02 — User manual | 30 | `[ ]` |
| ⬜ | 03 — Deployment guide | 30 | `[ ]` |
| ⬜ | 04 — Demo video and presentation deck | 30 | `[ ]` |
| ⬜ | 05 — Submission checklist | 31 | `[ ]` |
| ⬜ | 06 — Final tag and handover | 31 | `[ ]` |

**Milestone M5 exit criterion:** test suite green, traceability matrix complete,
report + manual + video + deck delivered.
**🚩 DOCUMENTATION FREEZE end of Day 29.**

---

## 2. Daily log

One row per working session. Be honest — a missed day recorded is worth more than a
gap that raises questions.

| Day | Date | What I actually did | Verified? | Commit | Blockers |
|---|---|---|---|---|---|
| 1 | Fri 6 Nov | Concept paper + proposal deck | ✅ | — | — |
| 2 | Sat 7 Nov | 4 UML diagrams + 4 overviews | ✅ | — | — |
| 3 | Sun 8 Nov | 4 EER/ER diagrams, 26 tables | ✅ | — | — |
| 4 | Mon 9 Nov | `schema_listing.md` + `consistency_report.md` | ✅ | — | — |
| 5 | Tue 10 Nov | Step 0.01 — `technology_stack.md` complete (§1–§7); A-13 decided and recorded as D-62; D-62 propagated to 27 across 16 files · Step 0.02 — root `README.md` · Step 0.03 — `design-freeze.md`; D-63 recorded. **Phase 0 closed.** *(Worked 11 Nov.)* | ✅ | — | — |
| 6 | Wed 11 Nov | Steps 1.01–1.04 — `git init` on `main`, `backend/`/`frontend/`/`tools/` created; `.gitignore` written **before** any `.env` existed; GitHub repo `sakay-ph-prac` created and the design phase pushed as 8 focused commits, not one blob; the freeze commit column filled so each of the 14 artefacts points at its introducing commit. *(Worked 13 Nov.)* | ✅ | `f7fe035`…`14812c1` | — |
| 7 | Thu 12 Nov | Steps 1.05–1.06 — `CONTRIBUTING.md` and the workflow conventions; `.venv` on Python 3.14.9 with 56 packages and no compiler invoked; backend scaffold (Django 6.1.3 + DRF, PyMySQL shim, `check` → 0 issues, `runserver` HTTP 200); frontend scaffold (Vue 3.5.45, Vite 8.3.8, Tailwind 4.3.5, 380 packages, dev server HTTP 200); `docker-compose.yml` validated with MySQL 8.4 + Redis 7-alpine healthy. **Defect found and fixed:** a `$` in `MYSQL_PASSWORD` made Compose interpolate it to empty while django-environ read it literally, so container and app held different passwords — proven before fixing (50 characters in `.env`, 47 passed by Compose), then fixed by regenerating the password and `docker compose down -v`. *(Worked 13 Nov.)* | ✅ | `cfa6e7f` `9e59550` | — |
| 8 | Fri 13 Nov | Step 2.01 — five apps, all 13 enums as `TextChoices`, shared abstract models, `PlatformConfig` (table 27); D-62's artefact-first requirement completed 14 Nov (schema listing + both EER sources + both PNGs re-rendered). *(Worked 13–14 Nov.)* | ✅ | `2e6f216` `d13d34b` | — |
| 9 | Sat 14 Nov | Step 2.02 — `.env`-driven settings; MySQL 8.4.13 proven on host port 3307; utf8mb4 on connection, server and collation with the `Barangay Peñaflor ₱25.00 🚐🛺` round-trip returning **MATCH**; Redis proven on both paths (cache db 1, channel layer db 0); `check` → 0 issues. Also 14 Nov: the booking fee's value decided — **D-64**, ₱3.00 flat, charged once per ride (log **D-18**). *(Worked 15 Nov.)* | ✅ | `d137254` | — |
| 10 | Sun 15 Nov | | | | |
| 11 | Mon 16 Nov | | | | |
| 12 | Tue 17 Nov | | | | |
| 13 | Wed 18 Nov | | | | |
| 14 | Thu 19 Nov | | | | |
| 15 | Fri 20 Nov | | | | |
| 16 | Sat 21 Nov | | | | |
| 17 | Sun 22 Nov | | | | |
| 18 | Mon 23 Nov | | | | |
| 19 | Tue 24 Nov | | | | |
| 20 | Wed 25 Nov | | | | |
| 21 | Thu 26 Nov | | | | |
| 22 | Fri 27 Nov | | | | |
| 23 | Sat 28 Nov | | | | |
| 24 | Sun 29 Nov | | | | |
| 25 | Mon 30 Nov | | | | |
| 26 | Tue 1 Dec | | | | |
| 27 | Wed 2 Dec | | | | |
| 28 | Thu 3 Dec | | | | |
| 29 | Fri 4 Dec | | | | |
| 30 | Sat 5 Dec | | | | |
| 31 | Sun 6 Dec | | | | |

---

## 3. Decision log

Every non-obvious choice, with the reason. This is the same discipline your
`consistency_report.md` already demonstrates — and it is what turns "I did it this
way" into "I can defend why".

> **Two numbering series, do not mix them up.** This log numbers its own decisions
> **D-01…D-18** — they are choices about how you work and what tools you use.
> `database/consistency_report.md` numbers **changes to the design** and continues
> from the original audit: **D-62** is A-13 (pricing), **D-63** is the `char(32)` UUID
> decision, **D-64** is the booking fee's value (14 Nov), and Phase 2's step-driven
> changes run on from **D-65**. Where a row here has a design consequence, it names
> the consistency-report number it produced — D-15 → D-63, D-17 → D-62, D-18 → D-64.
> All three are recorded, and both series are closed for Phase 0.
> `steps/phase-2-database/00-overview.md` holds the running table.

| # | Date | Decision | Alternatives considered | Reason |
|---|---|---|---|---|
| D-01 | 6 Nov | Python 3.14.9 + Django 6.1.3 | Node/Express, PHP/Laravel | Django's ORM and migrations map directly onto the 26-table design |
| D-02 | 6 Nov | MySQL 8.4 | PostgreSQL, SQLite | Already the tool used for the EER diagrams; Workbench matches |
| D-03 | 6 Nov | PyMySQL over `mysqlclient` | `mysqlclient` | Pure Python — no C compiler or client headers on Windows |
| D-04 | 6 Nov | Vue 3 over React | React, Svelte | Gentlest learning curve; SFCs map 1:1 onto the mockup screens |
| D-05 | 6 Nov | Tailwind over a component library | Vuetify, PrimeVue | Reproduces the mockup palette exactly, without fighting defaults |
| D-06 | 6 Nov | Leaflet + OSM | Google Maps | Free and keyless — no billing account |
| D-07 | 9 Nov | 26 tables, no SQL DDL generated | Generate DDL in the design phase | Listing is the written reference; migrations become the DDL in Phase 2 |
| D-08 | 10 Nov | **All 7 features in scope**, SOS + Bagyo simplified | 5 core only | Schema and mockups already support both; they are small additions |
| D-09 | 10 Nov | **Channels + Redis via Docker** | Memurai; HTTP polling | Standard, portable, one `docker compose up` |
| D-10 | 10 Nov | **One Vue app, role-based routes** | Two separate apps | Halves Phase 4; the driver screen shares palette and components |
| D-11 | 10 Nov | **`channels_redis` + `django-redis`**, one Redis, db 0 / db 1 | Two containers; LocMem | Isolation without a second service to operate |
| D-12 | 10 Nov | **No Celery** | Celery + Redis broker | Nothing needs an async worker; synchronous services + a management command suffice |
| D-13 | 10 Nov | **`simulate_driver` management command** | Manual position entry | Nothing else writes `TRIP_TRACKING`; the demo must move, reproducibly |
| D-14 | 10 Nov | **Simulated OTP**, returned in `DEBUG` | Real SMS gateway | A gateway costs money and needs a phone number |
| D-15 | 10 Nov | **Accept `char(32)` UUIDs** on MySQL | Custom `UUIDField` mapped to `BINARY(16)` | Django's default; stores the same value and indexes well. `BINARY(16)` halves the storage but needs a hand-written migration and breaks `UUIDField`'s admin and form handling. **Recorded as D-63 in `database/consistency_report.md` §3.11** |
| D-16 | 10 Nov | **English UI, Filipino feature names** | Add `vue-i18n` | The mockups already do this; translating 27 use cases earns no marks |
| D-17 | 11 Nov | **A-13 pricing gap resolved:** booking fee → new `RIDE_MODE.booking_fee`; commission rate → new `PLATFORM_CONFIG` table (27th table); chain-leg discount → **dropped**; `mock3` arithmetic → **corrected to ₱51.00** | (a) Leave the gap undocumented and invent the rules in Phase 3; (b) hardcode the rates in `FareCalculator`; (c) drop the booking fee; (d) implement the chain discount via a new `RIDE.chain_discount` column | The mockups show all three behaviours, so the schema had to carry them or the shipped UI would promise prices the backend could not reproduce. Rates belong in data, not code, so a rate change is a row edit rather than a deploy — but the waiver stays in code, because that is a rule and only its number is configurable. The chain discount was dropped because **no rule anywhere justifies it**; implementing it would mean inventing a business rule and then defending the invention, and the one thing the design does say about chains is that a chain's fare is the sum of its legs. **Recorded as D-62 in `database/consistency_report.md` §3.10.** Implemented in Phase 2 — `schema_listing.md` and both EER sources gained table 27 and `RIDE_MODE.booking_fee` in **Step 02.01**; the `booking_fee` model column lands in **Step 02.03** |
| D-18 | 14 Nov | **Booking fee is ₱3.00 flat on all six modes, charged once per ride** | (a) per-mode values; (b) ₱0 seed relying on the DDL default | ₱3.00 is the only artefact-traceable number — `mock3_payment.png`'s "Booking fee ₱3.00" line — and a flat per-booking fee is how Philippine platforms actually charge. On a ₱15 jeepney leg the 10% commission is ₱1.50, so the flat fee is the platform's meaningful take on the cheap modes where a percentage earns almost nothing. Once per ride, not per leg: a three-leg chain pays ₱3 in total, and `FareCalculator` reads it off `RIDE.mode_code` once at booking. **Recorded as D-64 in `database/consistency_report.md` §3.12** — seed lands in Step 02.08 |
| D-19 | 19 Nov | **Integrate Django auth with the domain USER table (Option A):** `AUTH_USER_MODEL = "accounts.User"`, `phone` as `USERNAME_FIELD`, `is_active` derived from `account_status`; USER gains `last_login` (D-66), `is_staff` (D-67), `is_superuser` (D-68), and `phone` becomes UNIQUE (D-69) | (B) keep `auth.User` for the admin and `accounts.User` for the domain — two identity systems; (C) hand-rolled JWT with no Django auth | One identity system means `request.user` is the same object everywhere; a dual system is a bug factory and hand-rolled auth reimplements password hashing for nothing. The three new columns are auth infrastructure, not domain. **Recorded as D-66..D-69 in `database/consistency_report.md` §3.14.** |

---

## 4. Blocker log

Anything that stopped work for more than an hour. Recording these is not
admitting failure — it is the raw material for the "challenges encountered"
section that every capstone report is expected to have.

| # | Day | Blocker | What I tried | Resolution | Days lost |
|---|---|---|---|---|---|
| B-01 | | | | | |

---

## 5. Traceability matrix

**Build this in Phase 6 — but start the habit now.** Every time you finish a step
that implements a use case, add its row. Filling this in retrospectively over 27
days of work is painful; filling it in as you go costs nothing.

This is the single highest-value document for CCS670: it is the artifact that
proves the object-oriented design was actually carried through to working
software.

| Requirement | Use case | Class | Table | Endpoint | Screen | Test | Status |
|---|---|---|---|---|---|---|---|
| *example* | Book Ride | `Passenger.bookRide()` | `RIDE` | `POST /api/rides/` | `mock1` | `test_book_ride` | `[ ]` |
| | | | | | | | |

*(A full scaffold with all 27 use cases is generated in Phase 6.)*

---

## 6. Session notes

Free-form. Anything that does not fit the tables above — a command that surprised
you, a version that turned out not to exist, a design assumption that broke.

### Day 5 — Tue 10 Nov *(worked 11 Nov)*

**Step 0.01 — technology stack document — DONE**

- Wrote **§3** — environment verification. Recorded verbatim output of `python`, `node`,
  `npm`, `pip`, `git`, `java`, `docker`. Docker Desktop is **not installed**; MySQL and
  Redis follow it, so all three are recorded as ⬜ Phase 1 rather than left blank
- Wrote **§4** — the `PyMySQL[rsa]` explanation: MySQL 8.4 defaults to
  `caching_sha2_password`, PyMySQL is pure Python with no OpenSSL bindings, so it cannot
  complete the RSA key exchange; the `rsa` extra supplies it. Pin: `PyMySQL[rsa]==1.2.3`
- Wrote **§5** — frontend rationale: Vue over React/Svelte, Vite, Tailwind over a
  component library, Leaflet+OSM, and **one app with role-based routes** rather than two
- Filled the two blank rows: `channels_redis` (db 0) and `django-redis` (db 1), one Redis
  container, two logical namespaces
- Added 13 new rows: daphne, Docker, geopy, pytest stack, vitest, ruff, eslint+prettier,
  GitHub Actions, `simulate_driver`, seed data, diagram tooling, simulated OTP
- Added **§6** "Considered and rejected" — Celery, `mysqlclient`, native UUID columns,
  Docker-for-Django, component library, `vue-i18n`, real SMS gateway, real payment
  provider, photo upload
- Added **§7** — version-verification stub, to be filled in Phase 1 Step 06. Flagged Vue
  Router 5 and Pinia 4 as the two pins most likely not to resolve
- Softened the intro claim: it no longer asserts every pin was verified; it points at §7
  for where that becomes evidence
- **Decided A-13** → recorded as **D-62** in `database/consistency_report.md` §3.10:
  booking fee → `RIDE_MODE.booking_fee`; commission → `PLATFORM_CONFIG` (table 27);
  chain discount → dropped; `mock3` arithmetic → corrected to ₱51.00
- Fixed two errors found in passing: the defect register said "All 44 are fixed" when it
  holds **61** entries; `§3`'s heading read "installed the system"
- Verified: no truncated sections, **no blank table cells**, all `§N` cross-references
  resolve, UTF-8 clean
- **Then propagated D-62 across the whole plan** — 16 files touched, because a design
  change that only half the documents know about is worse than no change at all:
  - 26 → 27 in every *forward-looking* document (Phase 2 overview, Step 02.01, Step
    02.08, Step 02.09, Phase 1 Step 06, `steps/README.md`, `PROGRESS.md` M2 criterion,
    audit §7). Historical rows — the Day 3/4 audit results, D-16/D-21/D-22 register
    entries — deliberately still read 26, because that is what was true then
  - `DOCUMENTED_TABLES` in Step 02.09 gained `PLATFORM_CONFIG`; the contract test's
    `== 27` assertion would otherwise have failed on the first run
  - `database/schema_listing.md` gained a **"Pending: table 27 (D-62)"** callout so the
    document is not silently wrong before Phase 2 edits it
  - `docs/plan/design-freeze.md` rows for the EER and the listing now name table 27 as a
    known post-freeze change rather than pretending the baseline is final
  - **Found and fixed a wrong cross-reference:** `booking_fee` lives on `RIDE_MODE`,
    which is written in **Step 02.03** (it has to come first so `Vehicle.mode` resolves),
    not Step 02.04. Five documents pointed at 02.04 — `consistency_report.md` §3.10, the
    roadmap risk register R7, audit A-13, and two places in `PROGRESS.md`
  - Un-gated the `booking_fee` block in Step 02.03: it was commented out behind "only if
    you took the A-13 recommendation", which is no longer a condition
- **Commit:** `38bd60e` (stack), `2ecf717` (database), `868e43b` (steps) — Day 6 first push

> **Note:** the design now has **27 tables**, not 26. `schema_listing.md` gains
> `PLATFORM_CONFIG` and `RIDE_MODE.booking_fee` in Phase 2, Steps 02.01 and 02.03, before
> the first migration. Until then D-62 is `decided`, not `implemented` — and any document
> still saying "26 tables" is describing the pre-D-62 design.

**Step 0.02 — root README — DONE**

- Wrote [`README.md`](../README.md) at the project root: what the project is, the seven
  features, a stack summary, the repository layout, a documentation index, the "Running it"
  placeholder and the milestone status table
- Wrote the opening description **in my own words** rather than quoting the concept
  paper's problem statement — a README that quotes the proposal reads as assembled
- **Documented why `database/` sits at the root** (A-12) instead of moving it: roughly
  thirty path references in `consistency_report.md` and `schema_listing.md` point at
  `database/...`, and moving it would break every one for a cosmetic gain
- Explained that `steps/` is the *build manual*, not documentation about the project —
  which is why `PROGRESS.md` lives there
- "Running it" left as an honest placeholder until Phase 1. A README claiming a setup
  procedure that does not exist is worse than one that admits the current state
- **Commit:** `9452a22` — Day 6 first push

**Step 0.03 — design freeze — DONE**

- Wrote [`docs/plan/design-freeze.md`](../docs/plan/design-freeze.md): 14 frozen
  artefacts, the five-step change procedure, **13 known limitations**, 3 open questions
  with decide-by dates, and a sign-off checklist
- **Recorded D-63** — UUID storage on MySQL — as a new register entry,
  `consistency_report.md` §3.11. MySQL 8.4 has no native `UUID` type, so Django's
  `UUIDField` stores every key as `CHAR(32)`. Left unrecorded, an assessor running
  `SHOW CREATE TABLE` would find `char(32)` where the design says `UUID` and have no way
  to tell a decision from a mistake. **Rejected** a custom `BINARY(16)` field: half the
  storage, but it needs a hand-written migration and breaks `UUIDField`'s admin and form
  handling for a saving nothing can measure
- Made the artefact change **first**, per the procedure: `schema_listing.md` gained an
  "About the `UUID` type" note before the register entry was written
- **No diagram re-render needed** — the EER diagrams show entities, keys and
  cardinalities; none of them display a storage type
- Fixed two errors found while writing the freeze:
  - The step file's artefact table listed the UML paths as `docs/uml/usecase_development.puml`.
    The real paths are nested one level deeper — `docs/uml/use-case/usecase_development.puml`.
    Corrected in the step file and in `schema_listing.md`'s source reference
  - The step file's limitation list had **item 13 duplicating §4's item 4**
    (`TRIP_TRACKING` pings belong to the ride, not the leg). Dropped the duplicate, so the
    freeze lists 13 limitations rather than 14 with one counted twice
- Dated the freeze **11 November**, not 10 — it is Day 5 work executed on Day 6, and the
  document says so rather than backdating itself
- **Commit column filled 13 Nov**, immediately after the first push. Each artefact now
  points at the commit that introduced it: `38bd60e` proposal/stack, `03f344f` UML,
  `2ecf717` database, `32817d4` mockups, `868e43b` plan/review/steps, `9452a22` README
- **Phase 0 complete.** The design does not change again without a D-number
- **Commit:** `868e43b` — Day 6 first push
