# Sakay.ph — Technology Stack

*Versions below were pinned against each project's public registry as of 6 November 2026.
Sections 3 and 7 record the environment and install verification performed on the development
machine. Compatibility between components was checked against each project's declared metadata
rather than assumed — but see §7, which is where that claim becomes verifiable rather than
asserted.*

---

## 1. Scope

The stack has to carry five things:

1. **A REST API** exposing the seven signature features (Lahat ng Sakyan, Isang Biyahe,
   Saan ang Jeep?, Pakyawan, Sertipikadong Manong, plus the two future-development features
   SOS Bantay and Bagyo Mode).
2. **A relational schema of 27 tables**, designed in `database/` — including a weak entity
   (`RIDE_LEG`), three associative entities, and a class-table inheritance split
   (`USER` → `PASSENGER` / `DRIVER`). The 27th, `PLATFORM_CONFIG`, was added on 11 Nov by
   decision **D-62**; the original design had 26.
3. **A mobile-web UI** matching the four mockups in `docs/mockups/` (390 × 844 CSS px phone
   screens, exported at 2× as 780 × 1688 PNGs).
4. **Live position data** for jeepney and UV Express tracking, and push notification for SOS.
5. **Simulated external providers** for payment and delivery, so no real money or credentials
   are ever involved.

---

## 2. Stack

| Component | Technology | Version | Why this choice |
|---|---|---|---|
| Backend language | Python | 3.14.9 | Installed and verified on the dev machine. Django 6.1 supports 3.12–3.14. |
| Backend framework | Django | **6.1.3** | Batteries-included: ORM, migrations, admin, auth. Bumped from 6.1.2 — Django only supports the newest patch in a series. |
| REST API | Django REST Framework | 3.18.3 | Current release (6 Oct 2026). Serializers map cleanly onto the 27-table schema. |
| ASGI server | **daphne** | 4.2.1 | Serves Channels' WebSockets. `runserver` alone cannot. Named in §1 but previously had no row. |
| **Frontend** | **Vue 3** | **3.5.45** | Gentlest learning curve of the major frameworks; first-party Vite integration; Single-File Components map 1:1 onto the four mockup screens. See §5. |
| Frontend routing | Vue Router | 5.4.0 | Official router. One route per mockup screen. **Major verified at install — resolved to 5.5.0; §7.** |
| Frontend state | Pinia | 4.1.0 | Official Vue store — holds the session, active ride, and live driver position. **Major verified at install — resolved to 4.1.0; §7.** |
| **Styling** | **Tailwind CSS** | **4.3.4** | Utility classes reproduce the mockup palette (`#1f4e79`, `#eef5fb`) exactly, with no fighting a component library's defaults. Tailwind 4 has no `tailwind.config.js` — tokens live in `@theme` inside CSS. |
| Build tool (frontend) | Vite | **8.3.6** | Bumped from 8.3.4. Requires Node `^20.19.0 \|\| >=22.12.0`; dev machine has 24.22.1. |
| Vue plugin for Vite | @vitejs/plugin-vue | 6.0.10 | Peer range `vite ^5 \|\| ^6 \|\| ^7 \|\| ^8` — Vite 8 is in range. |
| Tailwind plugin for Vite | @tailwindcss/vite | 4.3.4 | Peer `vite ^5.2 \|\| ^6 \|\| ^7 \|\| ^8`. Two lines of config, no PostCSS chain. |
| HTTP client (frontend) | axios | 1.21.0 | Interceptors handle JWT attach/refresh in one place. |
| Maps | Leaflet + OpenStreetMap | 1.9.4 | Free and keyless — nothing to sign up for, no billing. Backs *Saan ang Jeep?* and trip origin/destination. |
| Database | MySQL | 8.4.13 | LTS line (released 20 Oct 2026). **Django 6.1 requires MySQL 8.4+** — this is the floor, not a preference. Run via Docker Compose. |
| MySQL driver | PyMySQL | 1.2.3 | Pure Python — no C compiler or MySQL client headers on Windows. **Install as `PyMySQL[rsa]`** — see §4. |
| Database design & administration | MySQL Workbench | — | Matches MySQL 8.4; already the tool used for the EER diagrams. |
| Real-time / WebSockets | Django Channels | 4.3.2 | Live tracking and SOS push. Requires serving via ASGI (`daphne`), not WSGI. |
| Channel layer | `channels_redis` → Redis 7 | 4.3.0 | The only officially maintained channel layer for Channels 4.x. `InMemoryChannelLayer` cannot cross processes, so it breaks the moment `daphne` runs more than one worker; `channels_postgres` would add write load to the instance already serving every API call. |
| Cache / channel backend | `django-redis` → same Redis, db 1 | 6.0.0 | One container, two logical namespaces. `LocMemCache` is per-process, so each `daphne` worker would get its own cache — a bug that only appears under load. `DatabaseCache` writes to MySQL on every read, which is the opposite of what a cache is for. |
| Containers | Docker Desktop + Compose | 29.9.3 / v5.7.0 | Runs MySQL 8.4 and Redis 7. `docker compose up` is the whole environment setup. `utf8mb4` is mandatory — see the note below this table. |
| API authentication | djangorestframework-simplejwt | 5.5.1 | DRF ships no token scheme of its own. JWT access/refresh pair. |
| CORS | django-cors-headers | 4.9.0 | Vite dev server (:5173) and Django (:8000) are different origins — without this every API call fails. |
| API documentation | drf-spectacular | 0.30.0 | Auto-generates OpenAPI 3 / Swagger UI from the DRF views — a free deliverable for the submission. |
| Config & secrets | django-environ | 0.14.0 | DB password and adapter settings out of source control, into a `.env` file. |
| Geospatial | geopy | 2.4.1 | Great-circle distance for `Location.distanceTo()` and `MatchingEngine`'s `searchRadiusKm`. Hand-rolled haversine invites a silent unit bug. |
| Backend testing | pytest + pytest-django + pytest-cov + factory-boy | 9.0.1 / 4.12.0 / 7.1.0 / 3.3.3 | Nothing in the previous stack could run a test. `pytest-cov` supplies the coverage figure the final report cites. |
| Frontend testing | vitest + @vue/test-utils | 4.1.12 / 2.5.1 | Vite-native; shares `vite.config.js`. |
| Lint / format (Python) | ruff | 0.15.1 | One tool replacing flake8 + isort + black. |
| Lint / format (JS/Vue) | eslint + prettier + eslint-plugin-vue | 10.14.0 / 3.9.6 / 10.11.0 | Keeps the frontend presentable for grading. The `create-vue` template also ships `oxlint` 1.82.0 alongside ESLint — see §7. |
| CI | GitHub Actions | — | One workflow: `ruff`, `pytest`, `npm run build`. "The build is green" is worth showing an assessor. |
| Driver simulator | `simulate_driver` management command | — | Without it nothing writes `TRIP_TRACKING` rows and the live-tracking demo does not move. Same simulated-provider pattern as payment. |
| Seed data | Django fixtures + `seed_lookups` command | — | `RIDE_MODE`, `PAYMENT_METHOD`, `LGU_UNIT` are read by the whole app; with no seed the booking screen is empty. |
| Diagram tooling | PlantUML + Java + Graphviz | Java 22.0.1 | Already used for all 13 diagrams but previously absent from this table. **Java verified; the PlantUML jar and Graphviz `dot` were not on `PATH` at the Phase 1 check — confirm before the next re-render (§7).** **Pin `-DPLANTUML_LIMIT_SIZE=16384`** — defect D-61 is the reason: the default 4096 px silently clips a taller diagram while still exiting 0. |
| Payment service | Simulated provider adapter | — | No real payment integration. Adapter pattern over the `PAYMENT` / `DRIVER_PAYOUT` tables. |
| Delivery service | Simulated provider adapter | — | Same pattern; keeps the notification path testable without a live provider. |
| SMS / OTP | Simulated — Redis-cached OTP, returned in `DEBUG` | — | A real gateway costs money and needs a phone number. See §6. |
| Version control | Git | 2.56.0 | Installed and verified. |
| Remote repository | GitHub | — | Hosts the repository the instructor reviews; private with the instructor added as a collaborator. |
| Code editor | Visual Studio Code | — | Already in use for the UML and schema work; the Python, Vue and ESLint extensions cover this stack. |
| Node.js runtime | Node.js | 24.22.1 | Required by Vite 8. Installed. |
| Package manager | npm | 11.19.1 | Ships with Node. |

### Note — two Redis database indexes, and why `utf8mb4` is mandatory

**Two logical databases in one Redis container.** Redis ships with 16 logical databases.
The channel layer uses `/0` and the cache uses `/1`:

```python
# backend/config/settings/dev.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("REDIS_URL", default="redis://127.0.0.1:6379/0")]},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
```

Separate indexes keep channel-layer traffic and cache traffic from evicting each other under
a shared `maxmemory` policy, while costing nothing to operate. Two containers would buy
isolation this project does not need and a second service to keep running.

**`utf8mb4` is not optional.** Filipino place names (`Biñan`, `Peñaflor`) and the Tagalog UI
strings in the mockups contain characters outside MySQL's legacy `utf8`, which is 3-byte and
cannot store emoji at all — and `mock1_home.png` uses emoji as mode icons. Set it at the
server level, or the seed data fails to insert:

```yaml
# docker-compose.yml  (development only)
services:
  mysql:
    image: mysql:8.4
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
```

---

## 3. Verify what is currently installed

Recorded 11 November 2026; Docker and Compose re-checked 13 November 2026, after the
WSL 2 backend was installed and the daemon started:

```text
> python --version
Python 3.14.9

> node --version
v24.22.1

> npm --version
11.19.1

> git --version
git version 2.56.0.windows.1

> java -version
java version "22.0.1" 2024-04-16
Java(TM) SE Runtime Environment (build 22.0.1+8-16)
Java HotSpot(TM) 64-Bit Server VM (build 22.0.1+8-16, mixed mode, sharing)

> python -m pip --version
pip 26.2.2 from C:\Users\MCC IT Admin\AppData\Local\Programs\Python\Python314\Lib\site-packages\pip (python 3.14)

> docker --version
Docker version 29.9.3, build 5457199

> docker compose version
Docker Compose version v5.7.0
```

| Component | Required | Installed | Status |
|---|---|---|---|
| Python | 3.12–3.14 (Django 6.1 range) | 3.14.9 | ✅ |
| Node.js | `^20.19.0 \|\| >=22.12.0` (Vite 8) | 24.22.1 | ✅ |
| npm | — | 11.19.1 | ✅ |
| pip | — | 26.3 (in `.venv`) | ✅ |
| Git | — | 2.56.0.windows.1 | ✅ |
| Java | 17+ (PlantUML) | 22.0.1 | ✅ |
| Docker | — | 29.9.3 (WSL 2 backend) | ✅ |
| Docker Compose | v2+ | v5.7.0 | ✅ |
| MySQL | 8.4+ (Django 6.1 floor) | 8.4 via Docker, host port **3307** | ✅ |
| Redis | 7.x | 7-alpine via Docker, host port 6379 | ✅ |

**No gaps remain.** Docker Desktop is installed with the WSL 2 backend, and MySQL 8.4 and
Redis 7 run under `docker-compose.yml` — both report `healthy`, and `character_set_server`
is confirmed as `utf8mb4` with `collation_server` = `utf8mb4_unicode_ci`. The collation is
not decoration: the schema stores Tagalog diacritics (`ñ`) and emoji mode icons.

Two deviations, recorded rather than smoothed over. **Docker 29.9.3 and Compose v5.7.0 are
considerably newer than the versions this document was written against** — the plan assumed
a v2-era Compose. Nothing depends on the older behaviour, but a reader reproducing this on
a current Docker Desktop should expect the same versions rather than the ones originally
anticipated. **MySQL is published on host port 3307, not 3306**: a native `MySQL84` service
already owns 3306 on this machine. `MYSQL_PORT` in `.env` and the mapping in
`docker-compose.yml` must agree, or a fresh clone cannot connect.

Package-level verification (`pip install`, `npm install`) is recorded in §7 and, in full,
in `docs/plan/install-log.txt`.

Java is present at 22.0.1, which matters: every diagram in `docs/uml/` was rendered with it,
and it is what makes the `-DPLANTUML_LIMIT_SIZE=16384` fix in defect D-61 possible.

---

## 4. The `PyMySQL[rsa]` explanation

The MySQL driver row says *"Install as `PyMySQL[rsa]`"*. This is why.

MySQL 8.4 defaults to the `caching_sha2_password` authentication plugin. PyMySQL is pure
Python, so it has no OpenSSL bindings, and it therefore **cannot complete the RSA key
exchange** that `caching_sha2_password` requires over a non-TLS connection. The `rsa` extra
pulls in `cryptography`, which supplies it.

Without the extra, connecting to the database fails with:

```
pymysql.err.OperationalError: (2061, 'Authentication plugin
'caching_sha2_password' reported error: Authentication requires secure connection.')
```

So the pin is:

```
PyMySQL[rsa]==1.2.3
```

**Why this matters beyond the one error.** The alternative fix would be to leave the driver
plain and switch the MySQL user back to `mysql_native_password`. That trades a small,
well-understood dependency for a weaker authentication plugin, and it would need repeating
on every machine that runs the project. Taking the extra is the smaller commitment and the
one that survives a fresh clone.

---

## 5. The frontend rationale

The frontend row in §2 points here. Five choices, each with the alternative it beat.

**Why Vue 3 over React or Svelte.** Vue's learning curve is the gentlest of the three major
frameworks, which matters when the frontend is one phase of a one-month solo build rather
than the whole job. More concretely, Vue's Single-File Components map 1:1 onto the four
mockup screens — one `.vue` file per screen, with the template, the script and the styles in
one place. React would split each screen across a component file and a separate styling
solution; Svelte is smaller but has a thinner ecosystem for the routing and state libraries
this project needs.

**Why Vite.** It is Vue's first-party build tool, so the dev server and the production build
are the same tool with the same config. There is no separate bundler configuration to keep
in sync, and the dev server's hot reload is fast enough to make mockup-matching tolerable.

**Why Tailwind over a component library.** The mockups have a specific visual language — the
`#1f4e79` primary and `#eef5fb` surface, the mode chips, the status pills, the bottom sheet.
A component library (Vuetify, PrimeVue, Element Plus) would supply a finished look in an
hour and would look like every other Vue project; matching the mockup would mean overriding
its defaults everywhere. Utility classes reproduce the palette directly. Note that Tailwind 4
has no `tailwind.config.js` — design tokens are declared in `@theme` inside CSS, and every
Tailwind 3 tutorial found online will say otherwise.

**Why Leaflet + OpenStreetMap.** Free and keyless. Google Maps would need a billing account
and an API key that would then have to be kept out of the repository, for a feature whose
whole purpose is to show a dot moving along a line. Leaflet's `L.marker` handles the jeepney
icon with no extra package.

**Why one application with role-based routes rather than two.** The mockups show a passenger
app (four screens) and a driver app (one screen), and it is worth being explicit that these
are **one** Vue application behind a route guard, not two:

```
/                  → landing / role-aware redirect
/auth/*            → login, register, OTP
/passenger/*       → home, tracking, trips, payment, profile   (mock1–3)
/driver/*          → requests, my-uv, earnings, accreditation  (mock4)
/admin/*           → link out to Django admin
```

Two applications would double the scaffold, the router, the Pinia stores, the axios client,
the Tailwind tokens, the build and the deployment surface — for a second `<router-view>`.
`mock4_driver.png` shares the palette, the tab-bar pattern and the card components with the
passenger screens, so splitting them would mean building all of that twice and watching the
two copies drift within a day. One application with route guards produces the same
user-visible result and halves Phase 4.

---

## 6. Considered and rejected

Recorded so the reasoning is visible, and so "why didn't you use X?" has an answer that is
not a shrug. This is the same discipline `database/consistency_report.md` applies to design
defects.

| Rejected | Reason |
|---|---|
| **Celery + a broker** | Nothing in this system needs an asynchronous worker. The three candidates — matching timeout, payout settlement, surge-window expiry — are all fine as synchronous service calls plus a scheduled management command. Celery would add a broker, a worker process, and a class of bug (lost tasks, stale results) that a one-month solo build cannot afford. |
| **`mysqlclient`** | Requires a C compiler and MySQL headers on Windows. PyMySQL is pure Python and is chosen for exactly this reason. |
| **Native MySQL `UUID` columns** | MySQL 8.4 has a native `UUID` type, but Django's `UUIDField` maps to `char(32)`. `char(32)` stores the same value and indexes well, so this is accepted and documented as a divergence rather than fought — see D-63 in `database/consistency_report.md`. |
| **Dockerising Django itself** | Running the app natively while only MySQL and Redis run in Docker keeps `runserver` reload fast and the debugger attached. Containerising the application is a deployment concern, not a development one. |
| **A component library** (Vuetify / PrimeVue) | See §5 — Tailwind reproduces the mockup palette without fighting defaults, and adding a library would undo that. |
| **`vue-i18n`** | The mockups are already English with Filipino feature names. Adding i18n means translating 27 use cases' worth of strings for no marks. Recorded as a documented deviation (audit finding A-09). |
| **A real SMS / OTP gateway** | Costs money and needs a real phone number. Instead the OTP is generated, stored in the Redis cache with a TTL, and returned in the API response in `DEBUG`. The sequence diagram's `alt OTP verified / else OTP rejected` fragment is fully satisfiable this way. |
| **A real payment or delivery provider** | Same reasoning — no real money or credentials involved. Adapter pattern over `PAYMENT` / `DRIVER_PAYOUT` / `RECEIPT`, so a real provider is a class swap rather than a rewrite. |
| **Photo upload for driver profiles** | `Pillow` is a compiled extension and Python 3.14 is new enough that a wheel may not exist. `mock2` already uses initials and emoji avatars, so image upload earns nothing. |

---

## 7. Version verification

Completed 13 November 2026 (Phase 1, Step 06). This section is what turns the claim in the
introduction from an assertion into evidence. Raw output in `docs/plan/install-log.txt`.

### Backend

`pip install -r requirements/dev.txt` into `.venv` on Python 3.14.9. Exit code 0, 56
packages, no compiler invoked and no build step.

| Package | Pinned | Resolved | Note |
|---|---|---|---|
| Django | 6.1.3 | **6.1.3** | ✅ exact |
| djangorestframework | 3.18.3 | **3.18.3** | ✅ exact |
| djangorestframework-simplejwt | 5.5.1 | **5.5.1** | ✅ no ceiling conflict with Django 6.1 |
| django-cors-headers | 4.9.0 | **4.9.0** | ✅ exact |
| drf-spectacular | 0.30.0 | **0.30.0** | ✅ no ceiling conflict with Django 6.1 |
| django-environ | 0.14.0 | **0.14.0** | ✅ exact |
| PyMySQL[rsa] | 1.2.3 | **1.2.3** | ✅ pure Python — no client headers needed |
| channels | 4.3.2 | **4.3.2** | ✅ no ceiling conflict with Django 6.1 |
| channels-redis | 4.3.0 | **4.3.0** | ✅ no ceiling conflict with Django 6.1 |
| django-redis | 6.0.0 | **6.0.0** | ✅ exact |
| daphne | 4.2.1 | **4.2.1** | ✅ exact |
| geopy | 2.4.1 | **2.4.1** | ✅ exact |
| pytest | 9.0.1 | **9.0.1** | ✅ exact |
| pytest-django | 4.12.0 | **4.12.0** | ✅ exact |
| pytest-cov | 7.1.0 | **7.1.0** | ✅ exact |
| factory-boy | 3.3.3 | **3.3.3** | ✅ exact |
| ruff | 0.15.1 | **0.15.1** | ✅ exact |
| cryptography *(transitive, via `PyMySQL[rsa]`)* | — | **50.0.2** | ✅ prebuilt `cp311-abi3` wheel |

**Every backend pin resolved to exactly the version pinned**, and the four packages the
earlier draft of this section worried about — `channels`, `channels_redis`,
`djangorestframework-simplejwt`, `drf-spectacular` — all installed against Django 6.1.3 with
no ceiling conflict.

**The predicted risk did not materialise.** This plan flagged that `cryptography`, which
`PyMySQL[rsa]` needs for MySQL 8.4's `caching_sha2_password` plugin, might have no wheel for
Python 3.14 and would then need a Rust toolchain. It arrived as a prebuilt
`cryptography-50.0.2-cp311-abi3-win_amd64.whl`.

**One cosmetic oddity, recorded so it is not mistaken for a bad pin later.** `PyMySQL` 1.2.3
carries a stale legacy `__version__` string of `2.2.8`, while `pip show PyMySQL` and
`pymysql.VERSION` both report `(1, 2, 3, 'final')`. The tuple is authoritative.

### Frontend

`npm install` in `frontend/`, run three times (base template, then `axios leaflet`, then
`-D tailwindcss @tailwindcss/vite`), on Node 24.22.1 / npm 11.19.1. 380 packages.

| Package | Pinned | Resolved | Note |
|---|---|---|---|
| vue | 3.5.45 | **3.5.45** | ✅ exact |
| vue-router | 5.4.0 | **5.5.0** | ✅ **the major exists** — see below |
| pinia | 4.1.0 | **4.1.0** | ✅ exact |
| tailwindcss | 4.3.4 | **4.3.5** | ✅ patch drift |
| @tailwindcss/vite | 4.3.4 | **4.3.5** | ✅ patch drift |
| vite | 8.3.6 | **8.3.8** | ✅ patch drift |
| @vitejs/plugin-vue | 6.0.10 | **6.0.11** | ✅ patch drift |
| axios | 1.21.0 | **1.21.1** | ✅ patch drift |
| leaflet | 1.9.4 | **1.9.4** | ✅ exact |
| vitest | *pin at install* | **4.1.12** | ✅ |
| @vue/test-utils | *pin at install* | **2.5.1** | ✅ |
| eslint | *pin at install* | **10.14.0** | ✅ |
| prettier | *pin at install* | **3.9.6** | ✅ |
| jsdom | — | **30.1.3** | ✅ from the template |
| oxlint | — | **1.82.0** | ✅ from the template — not in the original table |

`frontend/package.json` declares `^` ranges rather than exact pins, so the patch drift above
is what a caret range does and is not a concern. The resolved versions are what is installed
and what the lockfile freezes.

**The two this plan flagged both resolved.** Vue Router resolved to `5.5.0` and Pinia to
`4.1.0`. The doubt recorded in the earlier draft — that the long-standing majors were Vue
Router 4 and Pinia 2, so the pins might name majors that do not exist — was wrong. Both
majors are real and current, and the question is settled in the project's favour.

**Additions the original stack table did not anticipate.** The `create-vue` template also
installs `oxlint` alongside ESLint, which current templates ship together, plus `jsdom`,
`prettier`, `npm-run-all2` and `vite-plugin-vue-devtools`. All development-only.

**`npm audit` reports 10 moderate advisories, all dev-only.** They are reached through
`@vue/test-utils` → `js-beautify` → `glob` and `eslint` → `@eslint/config-array` →
`minimatch`. Nothing in `vue`, `pinia`, `vue-router`, `axios` or `leaflet` is implicated, so
no advisory reaches a user of the application. `npm audit fix --force` would "resolve" them
by **downgrading** `@vue/test-utils` and `eslint` — trading working tooling for a clean
report. Recorded as a known limitation and deliberately not applied.

### Not verified by either command

`MySQL Workbench`, `GitHub Actions`, and the `PlantUML` / `Graphviz` diagram toolchain are
not installed by the two commands above. Java is present (`22.0.1`). The PlantUML jar and
Graphviz's `dot` binary were **not** resolved on `PATH` during this check — flagged rather
than fixed, because diagram re-rendering is a Phase 2+ activity. Confirm `dot` is reachable
before the next re-render, since the class and component diagrams need Graphviz layout.

**Rule if a pin ever fails to resolve:** drop the version, install the current release, and
update the table above. A stale pin that no longer matches what is installed is worse than
no pin, because it reads as verified when it is not.
