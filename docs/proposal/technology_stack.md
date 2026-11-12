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
| ASGI server | **daphne** | pin at install | Serves Channels' WebSockets. `runserver` alone cannot. Named in §1 but previously had no row. |
| **Frontend** | **Vue 3** | **3.5.45** | Gentlest learning curve of the major frameworks; first-party Vite integration; Single-File Components map 1:1 onto the four mockup screens. See §5. |
| Frontend routing | Vue Router | 5.4.0 | Official router. One route per mockup screen. **Re-verify this major at install — see §7.** |
| Frontend state | Pinia | 4.1.0 | Official Vue store — holds the session, active ride, and live driver position. **Re-verify this major at install — see §7.** |
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
| Channel layer | `channels_redis` → Redis 7 | pin at install | The only officially maintained channel layer for Channels 4.x. `InMemoryChannelLayer` cannot cross processes, so it breaks the moment `daphne` runs more than one worker; `channels_postgres` would add write load to the instance already serving every API call. |
| Cache / channel backend | `django-redis` → same Redis, db 1 | pin at install | One container, two logical namespaces. `LocMemCache` is per-process, so each `daphne` worker would get its own cache — a bug that only appears under load. `DatabaseCache` writes to MySQL on every read, which is the opposite of what a cache is for. |
| Containers | Docker Desktop + Compose | pin at install | Runs MySQL 8.4 and Redis 7. `docker compose up` is the whole environment setup. `utf8mb4` is mandatory — see the note below this table. |
| API authentication | djangorestframework-simplejwt | 5.5.1 | DRF ships no token scheme of its own. JWT access/refresh pair. |
| CORS | django-cors-headers | 4.9.0 | Vite dev server (:5173) and Django (:8000) are different origins — without this every API call fails. |
| API documentation | drf-spectacular | 0.30.0 | Auto-generates OpenAPI 3 / Swagger UI from the DRF views — a free deliverable for the submission. |
| Config & secrets | django-environ | 0.14.0 | DB password and adapter settings out of source control, into a `.env` file. |
| Geospatial | geopy | pin at install | Great-circle distance for `Location.distanceTo()` and `MatchingEngine`'s `searchRadiusKm`. Hand-rolled haversine invites a silent unit bug. |
| Backend testing | pytest + pytest-django + pytest-cov + factory-boy | pin at install | Nothing in the previous stack could run a test. `pytest-cov` supplies the coverage figure the final report cites. |
| Frontend testing | vitest + @vue/test-utils | pin at install | Vite-native; shares `vite.config.js`. |
| Lint / format (Python) | ruff | pin at install | One tool replacing flake8 + isort + black. |
| Lint / format (JS/Vue) | eslint + prettier + eslint-plugin-vue | pin at install | Keeps the frontend presentable for grading. |
| CI | GitHub Actions | — | One workflow: `ruff`, `pytest`, `npm run build`. "The build is green" is worth showing an assessor. |
| Driver simulator | `simulate_driver` management command | — | Without it nothing writes `TRIP_TRACKING` rows and the live-tracking demo does not move. Same simulated-provider pattern as payment. |
| Seed data | Django fixtures + `seed_lookups` command | — | `RIDE_MODE`, `PAYMENT_METHOD`, `LGU_UNIT` are read by the whole app; with no seed the booking screen is empty. |
| Diagram tooling | PlantUML + Java + Graphviz | pin at install | Already used for all 13 diagrams but previously absent from this table. **Pin `-DPLANTUML_LIMIT_SIZE=16384`** — defect D-61 is the reason: the default 4096 px silently clips a taller diagram while still exiting 0. |
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

Recorded 11 November 2026, verbatim from the development machine:

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
docker : The term 'docker' is not recognized as the name of a cmdlet, function, script file,
or operable program. Check the spelling of the name, or if a path was included, verify that
the path is correct and try again.
    + CategoryInfo          : ObjectNotFound: (docker:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException

> docker compose version
docker : The term 'docker' is not recognized as the name of a cmdlet, function, script file,
or operable program. Check the spelling of the name, or if a path was included, verify that
the path is correct and try again.
    + CategoryInfo          : ObjectNotFound: (docker:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
```

| Component | Required | Installed | Status |
|---|---|---|---|
| Python | 3.12–3.14 (Django 6.1 range) | 3.14.9 | ✅ |
| Node.js | `^20.19.0 \|\| >=22.12.0` (Vite 8) | 24.22.1 | ✅ |
| npm | — | 11.19.1 | ✅ |
| pip | — | 26.2.2 | ✅ |
| Git | — | 2.56.0.windows.1 | ✅ |
| Java | 17+ (PlantUML) | 22.0.1 | ✅ |
| Docker | — | not installed | ⬜ Phase 1, Step 06 |
| MySQL | 8.4+ (Django 6.1 floor) | via Docker | ⬜ Phase 1, Step 06 |
| Redis | 7.x | via Docker | ⬜ Phase 1, Step 06 |

**Two honest gaps.** Docker Desktop is not installed, so MySQL and Redis are not yet
available — all three are Phase 1 work and are recorded as such rather than left blank.
Package-level verification (`pip install`, `npm install`) is recorded in §7.

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

**Stub — completed in Phase 1, Step 06.** This section is what turns the claim in the
introduction from an assertion into evidence. Until the installers have actually run, the
claim is softened rather than trusted.

`pip install -r backend/requirements.txt` and `npm install` in `frontend/` will be run on
Day 7. Output recorded verbatim in `docs/plan/install-log.txt`.

| Package | Pinned | Resolved | Note |
|---|---|---|---|
| *(one row per dependency — filled in Phase 1, Step 06)* | — | — | — |

**Watch these two.** Vue Router and Pinia are pinned at majors that may not exist: for Vue 3
the long-standing majors are Vue Router 4 and Pinia 2, and this document pins Vue Router
`5.4.0` and Pinia `4.1.0`. Those may well be correct by November 2026 — but `npm install` is
where that is settled, and it is a two-minute fix on Day 7 versus a confusing afternoon on
Day 23.

**And these.** `channels`, `channels_redis`, `djangorestframework-simplejwt` and
`drf-spectacular` all track a very new Django. If any declares a ceiling below 6.1, the
install warns or fails. The fix is usually to take the current release and update this table.

If a pin does not resolve, **drop the version, install the current release, and update the
table** — a stale pin that no longer matches what is installed is worse than no pin, because
it reads as verified when it is not.
