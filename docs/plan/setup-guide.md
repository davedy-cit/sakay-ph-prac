# Sakay.ph — Setup Guide (New Machine, From Scratch)

A progressive, copy-paste manual for setting up the complete development
environment on a fresh Windows desktop. Written for someone who has never seen
this project: every command is paste-safe, every expected output is stated, and
every known trap is listed where you are about to hit it — with the full
troubleshooting table at the end.

**Audience:** the developer (or assessor) cloning `sakay-ph-prac` onto a new machine.
**Platform:** Windows 11 with PowerShell. **Time:** ~60–90 minutes, most of it downloads.
**Verified:** this is the exact sequence executed on the development machine
(see [`install-log.txt`](install-log.txt) for the recorded evidence).

---

## What you are installing

| Layer | Technology | Version | Comes from |
|---|---|---|---|
| Language | Python | 3.14.x | Installer (python.org) |
| Runtime | Node.js + npm | 24.x LTS | Installer (nodejs.org) |
| Version control | Git | 2.5x | Installer (git-scm.com) |
| Containers | Docker Desktop (+ WSL 2) | 29.x | Installer (docker.com) |
| Database | MySQL 8.4 | — | Docker image `mysql:8.4` |
| Cache / realtime | Redis 7 | — | Docker image `redis:7-alpine` |
| Backend | Django 6.1.3 + DRF 3.18 | 56 packages | `requirements/dev.txt` (exact pins) |
| Frontend | Vue 3.5 + Vite 8 + Tailwind 4 | 380 packages | `package.json` |

**End state:** MySQL and Redis running in Docker on ports **3307** and **6379**;
Django API at `http://127.0.0.1:8000` with a seeded database of 27 tables and a
working admin; Vue dev server at `http://localhost:5173`.

> **No C compiler is needed anywhere.** The MySQL driver is PyMySQL (pure
> Python — that is why it was chosen), so Python installs clean with no
> Visual Studio Build Tools. The one build-tool risk flagged in the plan
> (`cryptography` needing Rust on Python 3.14) did not materialise — it ships
> as a prebuilt wheel.

---

## Step 1 — Install the toolchain (~30 min, mostly downloads)

Install in this order. Docker last, because it needs WSL 2 and a restart.

1. **Git** — <https://git-scm.com/download/win>. Accept the defaults.
2. **Python 3.14** — <https://www.python.org/downloads/>. On the first
   installer screen, **tick "Add python.exe to PATH"** before clicking Install.
3. **Node.js 24 LTS** — <https://nodejs.org/>. Accept the defaults.
4. **Docker Desktop** — <https://www.docker.com/products/docker-desktop/>.
   Enable **WSL 2 backend** when offered. Reboot when it asks. Start Docker
   Desktop once and wait for the whale icon to go steady.

Then verify everything in a fresh PowerShell:

```powershell
git --version
python --version
node --version
npm --version
docker --version
docker compose version
```

Expected (versions may be slightly newer — that is fine; the dev machine
recorded Python 3.14.9, Node 24.22.1, npm 11.19.1, Git 2.56.0, Docker 29.9.3,
Compose v5.7.0):

```text
git version 2.5x.x.windows.1
Python 3.14.x
v24.x.x
11.x.x
Docker version 29.x.x, build ...
Docker Compose version v5.x.x
```

If `docker` is not recognised, Docker Desktop is not running — start it and retry.

---

## Step 2 — Clone the repository (~2 min)

```powershell
Set-Location "$HOME\Downloads"          # or wherever you keep projects
git clone https://github.com/davedy-cit/sakay-ph-prac.git
Set-Location sakay-ph-prac
```

All later commands assume you are in the repository root
(`...\sakay-ph-prac>`) unless a step says otherwise.

---

## Step 3 — Create the `.env` (~10 min)

The app reads every secret and environment-specific value from the root
`.env` through django-environ — nothing in `settings.py` is edited per machine.

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill in these values:

| Key | What to put |
|---|---|
| `DJANGO_SECRET_KEY` | Any long random string (50+ characters). One-liner below. |
| `MYSQL_PASSWORD` | 32 random **alphanumerics** — see the rule below |
| `MYSQL_ROOT_PASSWORD` | Same rules |
| `MYSQL_PORT` | Leave at **3307** — must match `docker-compose.yml`'s `3307:3306` |
| everything else | The template defaults are correct |

Generate values without leaving the terminal:

```powershell
# Secret key (printable, quoted-safe)
-join ((33..126) | Get-Random -Count 50 | ForEach-Object {[char]$_})

# DB passwords — alphanumerics only
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

> ⚠️ **The one rule that will bite you: no `$` in either password.** Docker
> Compose interpolates `$name` inside `.env` values and substitutes an empty
> string, while django-environ reads the file literally — so the container and
> the app end up holding **different** passwords. Every connection then fails
> with `Access denied for user 'sakayph'@'localhost'`, an error that points at
> the app rather than at the password. This defect was hit, proven (50
> characters in `.env`, 47 passed by Compose) and fixed on the dev machine.
> Alphanumerics only.

> ⚠️ **Port 3307, not 3306.** `docker-compose.yml` maps host 3307 → container
> 3306 (a native MySQL service owned 3306 on the dev machine). `MYSQL_PORT` in
> `.env` must stay **3307** or a fresh clone cannot connect.

`.env` is git-ignored — confirm with `git check-ignore -v .env`
(expected: `.gitignore:5:.env`). Never commit it.

---

## Step 4 — Start the services and prove them (~10 min)

```powershell
docker compose up -d
docker compose ps
```

Wait until both services show `healthy` — MySQL takes up to ~30 s on first
start (its `start_period`). If `docker compose ps` still shows `health:
starting`, wait 30 seconds and run it again. Do not run `migrate` before
MySQL is healthy.

**Prove MySQL is speaking `utf8mb4`** (mandatory — the schema stores `ñ` in
Tagalog place names and emoji mode icons; legacy 3-byte `utf8` rejects both):

```powershell
$root = (Select-String -Path .env -Pattern '^MYSQL_ROOT_PASSWORD=').Line.Split('=',2)[1]
docker compose exec mysql mysql -u root "-p$root" -e "SHOW VARIABLES LIKE 'character_set_server'; SHOW VARIABLES LIKE 'collation_server';"
```

Expected: `utf8mb4` and `utf8mb4_unicode_ci`.

**Prove Redis:**

```powershell
docker compose exec redis redis-cli ping
```

Expected: `PONG`.

---

## Step 5 — Backend: install, migrate, seed, admin (~15 min)

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements\dev.txt
```

Expected: **56 packages**, exit 0, **no compiler invoked**. Every pin in
`requirements/base.txt` + `dev.txt` (Django 6.1.3, DRF 3.18.3, PyMySQL[rsa]
1.2.3, Channels 4.3.2, …) resolves to exactly the pinned version.

> `config/__init__.py` registers `pymysql.install_as_MySQLdb()`, so PyMySQL is
> a drop-in for `mysqlclient` with zero C toolchain. The `[rsa]` extra supplies
> the cryptography that MySQL 8.4's `caching_sha2_password` auth requires —
> without it you get `Authentication requires secure connection` (error 2061).

Sanity-check the project wiring:

```powershell
Set-Location backend
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

Create the schema and seed the reference data:

```powershell
python manage.py migrate
python manage.py seed_lookups
python manage.py seed_lookups     # run twice — must be idempotent
```

Expected: migrations apply clean on the empty volume; the first `seed_lookups`
creates 17 reference rows (6 ride modes incl. `booking_fee` ₱3.00, 3 payment
methods, 4 LGU units, 4 platform-config keys); the **second run prints
`updated` for every row and creates nothing new** — idempotent, safe to re-run
after any reset.

Create the admin user — either answer the prompts:

```powershell
python manage.py createsuperuser
# Phone (USERNAME_FIELD): 0917xxxxxxx
# Full name: your name
# Role: ADMIN
# Password: your choice
```

…or non-interactively (password never typed at a prompt):

```powershell
$env:DJANGO_SUPERUSER_PHONE="09170000000"
$env:DJANGO_SUPERUSER_FULL_NAME="System Administrator"
$env:DJANGO_SUPERUSER_USER_ROLE="ADMIN"
$env:DJANGO_SUPERUSER_PASSWORD="<strong dev password>"
python manage.py createsuperuser --noinput
```

Start the API:

```powershell
python manage.py runserver
```

Expected: `Starting development server at http://127.0.0.1:8000/` with no
errors. Open `http://127.0.0.1:8000/admin/`, log in with the phone number, and
confirm **27 models** are listed across the five app sections (Accounts, Core,
Payments, Rides, Safety). Leave the server running for Step 6's CORS check —
or stop it with `Ctrl+C` and continue.

---

## Step 6 — Frontend (~10 min)

In a **second** terminal, from the repository root:

```powershell
Set-Location frontend
npm install
npm run dev
```

Expected: `npm install` → **380 packages** (vue 3.5.45, vite 8.3.8, tailwindcss
4.3.5, axios, leaflet, …); `npm run dev` → Vite ready in under a second.

> **Use `http://localhost:5173` — not `127.0.0.1:5173`.** Vite binds the IPv6
> loopback only, so the `127.0.0.1` form does not answer. This is recorded in
> `PROGRESS.md`'s verified-state table.

`npm audit` reports ~10 moderate advisories, all dev-only (reached through
`@vue/test-utils` and eslint). Do **not** run `npm audit fix --force` — it
"fixes" them by downgrading test tooling.

---

## Step 7 — Verify the whole system (~10 min)

Run every check; all must pass before you consider the machine set up.

| # | Check | Command | Expected |
|---|---|---|---|
| 1 | Django wiring | `python manage.py check` (in `backend/`) | 0 issues |
| 2 | Table count | block below | **27** |
| 3 | Encoding | block below | `City of Biñan`, hex ends `C3B1` |
| 4 | Admin | browser at `http://127.0.0.1:8000/admin/` | 27 models, login works |
| 5 | Frontend | `http://localhost:5173` | page renders |

**Check 2 — exactly 27 application tables** (from the repo root; `$pw` comes
from `.env`, and the `-p` flag is **glued** to it — `-p<password>`, never
`-p <password>`, which parses the password as a command):

```powershell
$pw = (Select-String -Path .env -Pattern '^MYSQL_PASSWORD=').Line.Split('=',2)[1]
docker compose exec mysql mysql -u sakayph "-p$pw" sakayph -N -e "
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema='sakayph'
  AND table_name NOT LIKE 'django_%'
  AND table_name NOT LIKE 'auth_%'
  AND table_name NOT LIKE 'USER_%';"
```

(`USER_groups` and `USER_user_permissions` are Django's own M2M tables, hence
the `USER_%` exclusion.)

**Check 3 — the encoding survived** — `ñ` in Biñan is the test:

```powershell
docker compose exec mysql mysql -u sakayph "-p$pw" sakayph -e "SELECT lgu_code, lgu_name FROM LGU_UNIT WHERE lgu_code='BIN-LAG';"
docker compose exec -T mysql mysql -u sakayph "-p$pw" sakayph -N -e "SELECT HEX(lgu_name) FROM LGU_UNIT WHERE lgu_code='BIN-LAG';"
```

Expected rows: `BIN-LAG  City of Biñan`, and hex
`43697479206F66204269C3B1616E` — `C3B1` is UTF-8 for `ñ`. (PowerShell console
rendering can mangle `ñ` visually; the hex check is the trustworthy one.)

If your machine's native `mysql` client (outside Docker) ever connects to the
container and gets `Access denied for user 'sakayph'@'localhost'` despite a
correct password, add `-h 127.0.0.1` — the container's user is `'sakayph'@'%'`,
and socket/localhost connections arrive as `@localhost`. The `docker compose
exec` form above does not need it.

---

## Resetting the environment

```powershell
docker compose down -v      # ⚠ destroys the database volume — all data gone
docker compose up -d
# wait for healthy, then in backend/:
python manage.py migrate
python manage.py seed_lookups
```

`down -v` (with `-v`) is the *full* reset. Plain `docker compose down` keeps
the volume. Note: MySQL's entrypoint creates the app user only when the data
directory is empty — so **after changing a password in `.env`, a `down -v` +
`up -d` is required**; editing `.env` alone leaves the old password inside the
volume and makes the fix look ineffective.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Access denied for user 'sakayph'@'localhost'` on every connection | A `$` in the password: Compose interpolated it to empty, Django read it literally | Regenerate the password alphanumerics-only, then `docker compose down -v` + `up -d` (entrypoint only creates the user on an empty data directory) |
| Same error from a native (host) `mysql` client with a correct password | Container user is `'sakayph'@'%'`; localhost connections arrive as `@localhost` | Add `-h 127.0.0.1` |
| `mysqladmin: Unknown command: 'sakayph'` | Space after `-p` | Glue it: `-p<password>`, or omit to be prompted |
| Django can't connect at all; you assumed 3306 | Compose maps **3307**→3306 | Keep `MYSQL_PORT=3307` in `.env` |
| `docker compose ps` shows `health: starting` forever | First-run MySQL initialisation | Wait ~30 s and re-check; check `docker compose logs mysql` if it never turns healthy |
| `Authentication requires secure connection` (PyMySQL error 2061) | `PyMySQL[rsa]` extra missing | Install from `requirements/dev.txt` as pinned — the `[rsa]` extra is load-bearing |
| `Error loading MySQLdb module` | PyMySQL shim not registered | Confirm `backend/config/__init__.py` calls `pymysql.install_as_MySQLdb()` |
| `migrate` fails immediately after `up -d` | MySQL not healthy yet | Wait for `docker compose ps` → healthy before migrating |
| Admin at `127.0.0.1:8000` says `DisallowedHost` | `DJANGO_ALLOWED_HOSTS` trimmed | Keep `localhost,127.0.0.1` in `.env` |
| `127.0.0.1:5173` does not answer but `localhost:5173` does | Vite binds IPv6 loopback only | Use `http://localhost:5173` |
| `seed_lookups` second run says `created` again | Not possible — the command is `update_or_create`-based | If you see it, you are on a different volume than you think; re-check `docker compose ps` |
| `docker` not recognised | Docker Desktop not running | Start it; wait for the whale to go steady |
| Compose warns `The "xyz" variable is not set` | `.env` missing or a key misspelled | `Copy-Item .env.example .env` and compare key names |

---

## Where the deeper evidence lives

| Document | What it holds |
|---|---|
| [`install-log.txt`](install-log.txt) | Verbatim toolchain/pip/npm output, services proof, 5 recorded deviations |
| [`technology_stack.md`](../proposal/technology_stack.md) | Why every component was chosen; §7 pin-vs-resolved verification table |
| [`design-freeze.md`](design-freeze.md) | The frozen design and its 14 documented limitations |
| [`../../README.md`](../../README.md) | The short "Running it" version of this guide |
| [`../../steps/PROGRESS.md`](../../steps/PROGRESS.md) | The day-by-day build log this setup was proven in |
