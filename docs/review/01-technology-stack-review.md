# Sakay.ph — Technology Stack Review

**Reviewed:** 10 November 2026
**Subject:** [../proposal/technology_stack.md](../proposal/technology_stack.md)
**Decisions applied:** all 7 features · Django Channels + Redis via Docker · window 6 Nov – 6 Dec 2026

---

## 1. Verdict

The chosen stack is **correct for this project**. Django + DRF + MySQL + Vue 3 +
Tailwind is a well-matched, teachable, well-documented combination, and the
reasoning in the doc's *"Why this choice"* column is sound — particularly the
PyMySQL choice (pure Python, so no C compiler on Windows) and Leaflet (keyless,
so no billing account).

Three problems stand in the way of using it:

1. **The document is truncated.** It ends mid-sentence at the §3 heading, and §4
   and §5 — both referenced from the body — do not exist.
2. **Two rows are blank** — the channel layer and the cache backend. Channels
   cannot run a multi-process channel layer without a backend, so this is a
   blocker, not a detail.
3. **Whole categories are absent** — testing, linting, CI, containers, geospatial,
   seed data, and a driver simulator. Some of these (the simulator especially) are
   needed for the demo to work at all.

---

## 2. Defects in the document itself

| ID | Severity | Defect |
|---|---|---|
| S-01 | **H** | File ends mid-sentence at line 63, `## 3. Verify what is currently installed the system`. Sections 3, 4 and 5 are missing |
| S-02 | **H** | Line 44 says *"Install as `PyMySQL[rsa]` (see §4)"* — **§4 does not exist**. The reader is sent to a section that isn't there |
| S-03 | **H** | Line 34 says *"See §5"* for the frontend rationale — **§5 does not exist** |
| S-04 | **H** | Lines 47–48 blank: `Channel layer`, `Cache / channel backend` |
| S-05 | M | The intro claims *"Every pinned version below was confirmed to exist in its public registry"* and *"Compatibility between components was checked against each project's declared metadata, not assumed."* That is a strong claim; §3 was evidently meant to carry the evidence for it and is empty. Either supply the evidence or soften the claim — an unverifiable assertion in a submitted document is worse than no assertion |
| S-06 | M | No version pins for Git, GitHub, VS Code, MySQL Workbench, Node — marked `—`. Acceptable, but the claim in S-05 then overreaches |
| S-07 | L | No `requirements.txt` or `package.json` accompanies the table, so the pins are prose rather than something installable |

**Fix:** [../../steps/phase-0-design-completion/01-complete-technology-stack.md](../../steps/phase-0-design-completion/01-complete-technology-stack.md)

---

## 3. The two blank rows — recommendation

Both should point at **one Redis instance**, which you have chosen to run in Docker.

### 3.1 Channel layer

| | |
|---|---|
| **Recommendation** | `channels_redis` (pin the current release at install time) |
| **Backed by** | Redis 7.x, `redis:7-alpine` image via Docker Compose |
| **Why** | It is the only officially maintained channel layer for Channels 4.x. The alternatives are unusable here: `InMemoryChannelLayer` cannot cross processes, so it breaks the moment `daphne` runs more than one worker; `channels_postgres` adds write load to the same MySQL/Postgres instance already serving every API call |
| **Serves** | *Saan ang Jeep?* live position push, SOS Bantay alerts, driver booking-request push |

```python
# backend/config/settings/dev.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("REDIS_URL", default="redis://127.0.0.1:6379/0")]},
    }
}
```

### 3.2 Cache / channel backend

| | |
|---|---|
| **Recommendation** | `django-redis` (pin the current release at install time) |
| **Backed by** | **The same Redis container, a different logical database** — channel layer on `/0`, cache on `/1` |
| **Why** | One container to run, one service to start, two logical namespaces. `LocMemCache` is per-process and would give each `daphne` worker its own cache — a bug that only appears under load. `DatabaseCache` writes to MySQL on every read, which is the opposite of what a cache is for |
| **Serves** | Session storage, fare-estimate caching, surge-window lookups (read on every booking), rate-limiting OTP attempts |

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
```

> **Why two database indexes rather than two containers.** Redis ships with 16
> logical databases. Separate indexes keep channel-layer traffic and cache
> traffic from evicting each other under a shared `maxmemory` policy, while
> costing nothing to operate. Two containers would buy isolation you do not need
> and a second service to keep running.

### 3.3 The Docker piece

```yaml
# docker-compose.yml  (development only)
services:
  mysql:
    image: mysql:8.4
    environment:
      MYSQL_DATABASE: sakayph
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    ports: ["3306:3306"]
    volumes: ["mysql_data:/var/lib/mysql"]
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: ["redis_data:/data"]
volumes:
  mysql_data:
  redis_data:
```

`utf8mb4` is **not optional** for this project: Filipino place names and the
Tagalog UI strings in your mockups include characters outside MySQL's legacy
`utf8` (which is 3-byte and cannot store emoji — and `mock1` uses emoji as mode
icons). Set it at the server level as above, or the seed data will fail to insert.

---

## 4. Missing stack — what to add

Grouped by when you need it. **Recommended** = add it. **Optional** = add only if
time allows. **Skip** = deliberately do not add, with the reason.

### 4.1 Needed before the first commit (Phase 1)

| Component | Choice | Why |
|---|---|---|
| Container runtime | Docker Desktop | You chose Redis-in-Docker. Also gives you MySQL 8.4 without a native install, so `docker compose up` is the entire environment setup |
| Python env | `venv` (stdlib) | No Poetry/uv needed for a solo project; `venv` + `requirements.txt` is one less tool to explain in the report |
| Dependency pinning | `requirements.txt` with `==` pins, split `base` / `dev` | The stack doc pins versions in prose; this makes them installable and reproducible |
| Secrets | `.env` + `.env.example` | `django-environ` is already chosen. `.env.example` is committed, `.env` is git-ignored |

### 4.2 Needed to build the backend (Phase 2–3)

| Component | Choice | Why |
|---|---|---|
| **ASGI server** | `daphne` | Named in the stack doc's prose but **has no row**. Channels needs ASGI; `runserver` alone will not serve WebSockets. `daphne` is Channels' own server, so it is the fewest moving parts. `uvicorn` also works if you prefer it |
| **Test framework** | `pytest` + `pytest-django` + `pytest-cov` | **Nothing in the current stack can run a test.** Django's own `TestCase` would work, but pytest's fixtures and assertion output are markedly better, and `pytest-cov` gives you the coverage number the final report should cite |
| **Test data** | `factory-boy` | You will create passengers, drivers, rides and payments in dozens of tests. Hand-writing constructors does not scale past ~10 tests |
| **Geospatial** | `geopy` | `Location.distanceTo(other)` and `MatchingEngine.matchDriver(ride, searchRadiusKm)` both need great-circle distance. `geopy.distance.geodesic` is two lines and well-tested; hand-rolling haversine invites a silent unit bug |
| **Lint + format** | `ruff` | One tool for both, extremely fast, replaces flake8 + isort + black. Keeps the codebase presentable for grading |
| **Seed data** | Django fixtures + a `seed` management command | `RIDE_MODE`, `PAYMENT_METHOD`, `LGU_UNIT` are lookup tables the whole app reads (A-11) |
| **Driver simulator** | A `simulate_driver` management command | **See §6.2 — without this you cannot demo live tracking.** No row in the stack doc covers it |
| **Git hooks** | `pre-commit` (optional) | Runs `ruff` before each commit. Nice-to-have; skip if it slows you down |

### 4.3 Needed to build the frontend (Phase 4)

| Component | Choice | Why |
|---|---|---|
| **Test framework** | `vitest` + `@vue/test-utils` | Vite-native, shares your `vite.config.js`. Nothing in the stack can currently test a component |
| **Lint + format** | `eslint` + `prettier` + `eslint-plugin-vue` | Same rationale as `ruff` |
| **HTTP mock** | `msw` (optional) | Lets you build screens before the API is finished. Useful if backend slips |
| **Map markers** | `leaflet` (already listed) | No extra package — Leaflet's `L.marker` handles the jeepney icon |

### 4.4 Needed before submission (Phase 5–6)

| Component | Choice | Why |
|---|---|---|
| **CI** | GitHub Actions | One workflow running `ruff`, `pytest`, `npm run build`. It is cheap to add, and "the build is green" is a strong thing to show an assessor |
| **API collection** | `requests.http` files, or the Swagger UI from `drf-spectacular` | `drf-spectacular` is already in the stack and gives you interactive docs free. A `.http` file additionally lets a grader replay your demo without a frontend |
| **Diagram renderer** | PlantUML + Java + Graphviz | Used already but **absent from the table** (A-10). Pin `-DPLANTUML_LIMIT_SIZE=16384` — defect D-61 is the reason |
| **Static files** | `whitenoise` (optional) | Only if you deploy. Not needed for a local demo |

### 4.5 Deliberately not adding

Record these in the stack doc as **considered and rejected** — it reads far better
than silence, and it is the same discipline your consistency report already shows.

| Rejected | Reason |
|---|---|
| **Celery + a broker** | Nothing in this system needs an asynchronous worker. The three candidates — matching timeout, payout settlement, surge-window expiry — are all fine as synchronous service calls plus a scheduled management command. Celery would add a broker, a worker process, and a class of bug (lost tasks, stale results) that a 26-day solo build cannot afford |
| **`mysqlclient`** | Requires a C compiler and MySQL headers on Windows. PyMySQL is already chosen correctly for this reason |
| **Native MySQL UUID columns** | See §5.3 — Django maps `UUIDField` to `char(32)` on MySQL. Accept and document |
| **Docker for Django itself** | Running the app natively and only MySQL/Redis in Docker keeps `runserver` reload fast and the debugger attached. Containerising the app is a deployment concern, not a development one |
| **A component library** (Vuetify/PrimeVue) | The stack doc already reasons correctly that Tailwind reproduces the mockup palette without fighting defaults. Adding one would undo that |
| **`vue-i18n`** | The mockups are already English with Filipino feature names. Adding i18n means translating 27 use cases' worth of strings for no marks. Document the deviation instead (A-09) |

---

## 5. Version and compatibility risks

### 5.1 Re-verify every pin before you build on it

The doc's intro asserts every pin was confirmed against its registry. **Do not
rely on that assertion** — including my own reading of it. Verify mechanically, at
install time, where a wrong major version fails loudly instead of silently:

```powershell
# Backend — inside the venv, after writing requirements.txt
pip install -r requirements.txt

# Frontend — in frontend/
npm install
```

Both commands either resolve or fail. Run them in Phase 1 **before** writing
application code, so a bad pin surfaces on Day 5 rather than Day 20. If a pin does
not resolve, drop the version and install the current release, then update the
table — and record the change in the stack doc rather than leaving it stale.

> Pay particular attention to **Vue Router** and **Pinia**. For Vue 3 the
> long-standing majors are Vue Router 4 and Pinia 2; the doc pins Vue Router
> `5.4.0` and Pinia `4.1.0`. Those may well be correct by November 2026 — but if
> they are not, `npm install` is where you find out, and it is a two-minute fix
> now versus a confusing afternoon later.

### 5.2 Python 3.14 is very new

3.14.9 is bleeding-edge. The stack doc is right that Django 6.1 supports 3.12–3.14,
and right that PyMySQL being pure Python avoids the usual wheel problem. The
residual risk is **any package with a compiled extension**:

- `Pillow` — only needed if you add photo upload (driver profile photos). If a 3.14
  wheel is missing, you will need a compiler. **Avoid image upload; use initials
  or emoji avatars**, which is what `mock2` already does.
- `geopy`, `django-redis`, `channels_redis`, `factory-boy`, `pytest` — all pure
  Python. Safe.

**Mitigation:** add every dependency in Phase 2 and run `pip install` immediately,
so a missing wheel is discovered on Day 8, not Day 25.

### 5.3 UUID storage deviates from the schema listing

`schema_listing.md` declares `user_id UUID`, `ride_id UUID`, and 20 more.
Django's `UUIDField` on MySQL creates **`char(32)`**, not a native `UUID` type.
MySQL 8.4 does have a native `UUID` type, but Django does not use it.

**This is not a defect** — `char(32)` stores the same value and indexes well.
But it *is* a divergence between the design document and the built database, and
your consistency report has trained a reader to expect such divergences to be
documented.

**Do:** record it as a new entry (D-63) in `database/consistency_report.md`, and
verify it in the Phase 2 step by diffing the generated DDL against the listing.

### 5.4 `channels` / DRF against Django 6.1

Both are third-party packages tracking a very new Django. If either declares a
ceiling below 6.1, `pip install` warns or fails. Discover it in Phase 1 alongside
§5.1 — the fix is usually to take the current release.

---

## 6. Two architectural decisions the stack doc does not make

### 6.1 One Vue app or two?

The mockups show a passenger app (4 screens) and a driver app (1 screen), and the
stack doc does not say whether these are one application or two.

**Recommendation: one Vue application, role-based routing.**

```
/                  → landing / role-aware redirect
/auth/*            → login, register, OTP
/passenger/*       → home, tracking, trips, payment, profile   (mock1–3)
/driver/*          → requests, my-uv, earnings, accreditation  (mock4)
/admin/*           → optional: link out to Django admin
```

**Why.** Two apps double the scaffold, the router, the Pinia stores, the axios
client, the Tailwind config, the build and the deployment surface — for a second
`<router-view>`. One app with route guards gets the same user-visible result and
halves Phase 4. `mock4_driver.png` shares the palette, the tab-bar pattern and the
card components with the passenger screens; splitting them would mean building all
of that twice.

### 6.2 How does live tracking actually move?

*Saan ang Jeep?* is one of the five signature features, and the demo depends on a
vehicle visibly moving on the Leaflet map. But **there are no real drivers, no GPS
hardware, and no phones in the field** — so nothing will write `TRIP_TRACKING` rows
on its own, and the map will sit still.

The stack doc's *"Simulated provider adapter"* rows cover payment and delivery.
**No row covers position.**

**Recommendation: add a `simulate_driver` management command.**

```
python manage.py simulate_driver --ride <ride_id> --speed 30 --interval 2
```

It walks a driver along the leg's origin→destination line and writes a
`TRIP_TRACKING` row every `interval` seconds, which the channel layer then pushes
to the passenger's map. This is the same *simulated external provider* pattern the
stack doc already applies to GCash and Maya — so it is consistent with the design,
not a workaround. It also makes your demo reproducible: the same command produces
the same movement every time, which matters when you record the video.

Add it to the stack table as a row, and give it a step file in Phase 3.

### 6.3 OTP has no provider

`Verify Identity (OTP / valid ID)` is a use case and `PASSENGER.verified_at` is a
column, but the stack lists no SMS gateway. **Do not add one** — it costs money and
needs a real phone number. Instead: generate the OTP, store it in the Redis cache
with a TTL, and in `DEBUG` return it in the API response and log it to the
console. Document this as a simulated provider alongside payment. Your sequence
diagram's `alt OTP verified / else OTP rejected` fragment is fully satisfiable this
way.

---

## 7. Completed stack table — drop-in replacement for §2

Rows marked **＋** are new. Rows marked **✎** replace a blank. Everything else is
the author's original text, preserved.

| Component | Technology | Version | Why this choice |
|---|---|---|---|
| Backend language | Python | 3.14.9 | Installed and verified on the dev machine. Django 6.1 supports 3.12–3.14. |
| Backend framework | Django | **6.1.3** | Batteries-included: ORM, migrations, admin, auth. Bumped from 6.1.2 — Django only supports the newest patch in a series. |
| REST API | Django REST Framework | 3.18.3 | Current release (6 Oct 2026). Serializers map cleanly onto the 26-table schema (27 after D-62). |
| **ASGI server** ＋ | **daphne** | pin at install | Serves Channels' WebSockets. `runserver` alone cannot. Named in §1 but previously had no row. |
| **Frontend** | **Vue 3** | **3.5.45** | Gentlest learning curve of the major frameworks; first-party Vite integration; Single-File Components map 1:1 onto the four mockup screens. |
| Frontend routing | Vue Router | 5.4.0 | Official router. One route per mockup screen. **Re-verify this major at install — see §5.1.** |
| Frontend state | Pinia | 4.1.0 | Official Vue store — holds the session, active ride, and live driver position. **Re-verify this major at install — see §5.1.** |
| **Styling** | **Tailwind CSS** | **4.3.4** | Utility classes reproduce the mockup palette (`#1f4e79`, `#eef5fb`) exactly, with no fighting a component library's defaults. |
| Build tool (frontend) | Vite | **8.3.6** | Bumped from 8.3.4. Requires Node `^20.19.0 \|\| >=22.12.0`; dev machine has 24.22.1. |
| Vue plugin for Vite | @vitejs/plugin-vue | 6.0.10 | Peer range `vite ^5 \|\| ^6 \|\| ^7 \|\| ^8` — Vite 8 is in range. |
| Tailwind plugin for Vite | @tailwindcss/vite | 4.3.4 | Peer `vite ^5.2 \|\| ^6 \|\| ^7 \|\| ^8`. Two lines of config, no PostCSS chain. |
| HTTP client (frontend) | axios | 1.21.0 | Interceptors handle JWT attach/refresh in one place. |
| Maps | Leaflet + OpenStreetMap | 1.9.4 | Free and keyless — nothing to sign up for, no billing. Backs *Saan ang Jeep?* and trip origin/destination. |
| Database | MySQL | 8.4.13 | LTS line (released 20 Oct 2026). **Django 6.1 requires MySQL 8.4+** — this is the floor, not a preference. Run via Docker Compose. |
| MySQL driver | PyMySQL | 1.2.3 | Pure Python — no C compiler or MySQL client headers on Windows. **Install as `PyMySQL[rsa]`** (see §8). |
| Database design & administration | MySQL Workbench | — | Matches MySQL 8.4; already the tool used for the EER diagrams. |
| Real-time / WebSockets | Django Channels | 4.3.2 | Live tracking and SOS push. Requires serving via ASGI (`daphne`), not WSGI. |
| **Channel layer** ✎ | **`channels_redis` → Redis 7** | pin at install | **See §3.1.** The only officially maintained channel layer for Channels 4.x. `InMemoryChannelLayer` cannot cross processes. |
| **Cache / channel backend** ✎ | **`django-redis` → same Redis, db 1** | pin at install | **See §3.2.** One container, two logical namespaces. `LocMemCache` is per-process and breaks under multiple `daphne` workers. |
| **Containers** ＋ | **Docker Desktop + Compose** | pin at install | Runs MySQL 8.4 and Redis 7. `docker compose up` is the whole environment setup. `utf8mb4` is mandatory for the Tagalog/emoji content. |
| API authentication | djangorestframework-simplejwt | 5.5.1 | DRF ships no token scheme of its own. JWT access/refresh pair. |
| CORS | django-cors-headers | 4.9.0 | Vite dev server (:5173) and Django (:8000) are different origins — without this every API call fails. |
| API documentation | drf-spectacular | 0.30.0 | Auto-generates OpenAPI 3 / Swagger UI from the DRF views — a free deliverable for the submission. |
| Config & secrets | django-environ | 0.14.0 | DB password and adapter settings out of source control, into a `.env` file. |
| **Geospatial** ＋ | **geopy** | pin at install | Great-circle distance for `Location.distanceTo()` and `MatchingEngine`'s `searchRadiusKm`. Hand-rolled haversine invites a silent unit bug. |
| **Backend testing** ＋ | **pytest + pytest-django + pytest-cov + factory-boy** | pin at install | **Nothing in the previous stack could run a test.** pytest-cov supplies the coverage figure the final report cites. |
| **Frontend testing** ＋ | **vitest + @vue/test-utils** | pin at install | Vite-native; shares `vite.config.js`. |
| **Lint / format (Python)** ＋ | **ruff** | pin at install | One tool replacing flake8 + isort + black. |
| **Lint / format (JS/Vue)** ＋ | **eslint + prettier + eslint-plugin-vue** | pin at install | Keeps the frontend presentable for grading. |
| **CI** ＋ | **GitHub Actions** | — | One workflow: `ruff`, `pytest`, `npm run build`. "The build is green" is worth showing an assessor. |
| **Driver simulator** ＋ | **`simulate_driver` management command** | — | **See §6.2.** Without it nothing writes `TRIP_TRACKING` rows and the live-tracking demo does not move. Same simulated-provider pattern as payment. |
| **Seed data** ＋ | **Django fixtures + `seed` command** | — | `RIDE_MODE`, `PAYMENT_METHOD`, `LGU_UNIT` are read by the whole app; with no seed the booking screen is empty. |
| **Diagram tooling** ＋ | **PlantUML + Java + Graphviz** | pin at install | Already used for all 13 diagrams but absent from this table. **Pin `-DPLANTUML_LIMIT_SIZE=16384`** — defect D-61 is the reason. |
| Payment service | Simulated provider adapter | — | No real payment integration. Adapter pattern over the `PAYMENT` / `DRIVER_PAYOUT` tables. |
| Delivery service | Simulated provider adapter | — | Same pattern; keeps the notification path testable without a live provider. |
| **SMS / OTP** ＋ | **Simulated — Redis-cached OTP, returned in `DEBUG`** | — | **See §6.3.** A real gateway costs money and needs a phone number. |
| Version control | Git | 2.56.0 | Installed and verified. |
| Remote repository | GitHub | — | |
| Code editor | Visual Studio Code | — | |
| Node.js runtime | Node.js | 24.22.1 | Required by Vite 8. Installed. |
| Package manager | npm | 11.19.1 | Ships with Node. |

---

## 8. Note on `PyMySQL[rsa]`

The stack doc line 44 says to install `PyMySQL[rsa]` and points at a §4 that does
not exist. The reason, so it is on the record:

MySQL 8.4 defaults to `caching_sha2_password` authentication. PyMySQL is pure
Python, so it has no OpenSSL bindings, and it therefore **cannot complete the
RSA key exchange** that `caching_sha2_password` requires over a non-TLS
connection. The `rsa` extra pulls in `cryptography`, which supplies it. Without
the extra, connecting gives:

```
pymysql.err.OperationalError: (2061, 'Authentication plugin
'caching_sha2_password' reported error: Authentication requires secure connection.')
```

So the pin is:

```
PyMySQL[rsa]==1.2.3
```

This belongs in `requirements.txt` from Day 5, and the reasoning belongs in §4 of
the stack document once you write it.

---

## 9. Summary of what to change in `technology_stack.md`

1. Write the missing **§3** (environment verification — record actual output of
   `python --version`, `node --version`, `docker --version`, `git --version`).
2. Write the missing **§4** — the `PyMySQL[rsa]` explanation from §8 above.
3. Write the missing **§5** — the frontend rationale the doc already points to.
4. Fill the two blank rows from **§3.1** and **§3.2** above.
5. Add the **＋** rows from §7.
6. Add a **§6 "Considered and rejected"** section from §4.5 — it matches the
   discipline your consistency report already demonstrates.
7. Add a **§7 "Version verification"** section recording the actual `pip install`
   and `npm install` output from Phase 1, which is what makes the intro's claim
   about verified pins true rather than asserted.
8. Soften or substantiate the intro's claim about every pin having been verified —
   see S-05.

**Step-by-step instructions:** [../../steps/phase-0-design-completion/01-complete-technology-stack.md](../../steps/phase-0-design-completion/01-complete-technology-stack.md)
