# Step 1.06 — Scaffold Django and Vue, Prove the Environment

| | |
|---|---|
| **Goal** | MySQL and Redis run in Docker; both scaffolds install clean; `runserver` and `npm run dev` both serve a page. The version risks are now facts, not assumptions |
| **Day / Time** | Day 7 (Thu 12 Nov) · ~2–3 hours |
| **Prerequisites** | [Step 1.05](05-workflow-conventions.md) |
| **Produces** | `docker-compose.yml`, `requirements/base.txt`, `requirements/dev.txt`, `backend/` Django project, `frontend/` Vue app, `docs/plan/install-log.txt` |

---

## Why this step exists and why it is not optional

Every other step in this phase produces files. This one produces **evidence**.

Right now the stack document lists versions you have not installed. Risks R2, R3, R4
and R6 in the roadmap are all versions of the same worry: *what if the pin does not
resolve on this machine?* There are four realistic failure modes:

| Risk | What it looks like | Cost if found on Day 15 |
|---|---|---|
| R2 — Python 3.14 wheel gap | `pip install` tries to compile `mysqlclient` or `cryptography` from source and fails | Days |
| R3 — Django 6.1 / Channels compatibility | `channels` imports something Django 6.1 removed | Days |
| R4 — Node 24 / Vite 8 incompatibility | `npm run dev` crashes on startup | Hours |
| R6 — Docker not installed or not running | `docker compose up` fails, no database, everything stops | Hours, and it blocks the whole of Phase 2 |

Finding any of these **today** costs you an afternoon. Finding them on Day 15 costs
you the project. That asymmetry is the entire reason for this step.

**The rule for this step:** you are not building anything. You are installing
things and proving they start. If you find yourself writing application code, stop.

---

## Do this

### 1. Verify the toolchain is actually installed (~15 min)

Do not assume. Run all of these and record the output — you will paste it into
`docs/plan/install-log.txt` at the end.

```powershell
python --version
pip --version
node --version
npm --version
git --version
docker --version
docker compose version
```

Expected, from the technology stack:

| Tool | Expected |
|---|---|
| Python | 3.14.x |
| Node | 24.x |
| npm | 11.x |
| Git | 2.5x |
| Docker | 2x.x |
| Docker Compose | v2.x (the `docker compose` subcommand, not `docker-compose`) |

**Docker is the one to check carefully.** Two failure modes:

```powershell
# 1. Is the CLI installed at all?
docker --version

# 2. Is the daemon actually running?
docker info
```

If `docker --version` works but `docker info` says *"error during connect"* or
*"cannot connect to the Docker daemon"*, Docker Desktop is installed but not
started. Launch **Docker Desktop** from the Start menu and wait for the whale icon
to stop animating. This is not a bug — it is how Docker Desktop works on Windows.

If `docker` is not recognised at all:

```powershell
winget install --id Docker.DockerDesktop
```

Then reboot. Docker Desktop needs WSL 2, and the installer will offer to enable it.

> **If Docker cannot be made to work today, stop and tell me.** There is a fallback
> (MySQL and Redis installed natively on Windows, or MySQL in XAMPP plus a Redis
> binary), but it changes `.env`, `settings.py`, and the README's setup section. It
> is much cheaper to decide this today than in Phase 2.

---

### 2. Write `docker-compose.yml` (~30 min)

At the **project root** — not inside `backend/`. The compose file describes the
whole system's services, and it will later hold more than the database.

```yaml
# docker-compose.yml
# Development services for Sakay.ph.
# Start:  docker compose up -d
# Stop:   docker compose down
# Reset:  docker compose down -v   (DESTROYS the database volume)

services:
  mysql:
    image: mysql:8.4
    container_name: sakayph-mysql
    restart: unless-stopped
    environment:
      MYSQL_DATABASE: ${MYSQL_DATABASE:-sakayph}
      MYSQL_USER: ${MYSQL_USER:-sakayph}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-sakayph}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpw}
    ports:
      # Host 3307 → container 3306. A native MySQL 8.4 service owns host 3306
      # on this machine, so the container is published on 3307 instead.
      - "3307:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-p${MYSQL_ROOT_PASSWORD:-rootpw}"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

  redis:
    image: redis:7-alpine
    container_name: sakayph-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  mysql_data:
  redis_data:
```

**Three things in that file are load-bearing:**

| Setting | Why it matters |
|---|---|
| `--character-set-server=utf8mb4` | The app stores Tagalog text with diacritics and emoji transport icons. MySQL's default `latin1` mangles both, and the corruption is silent until you read the data back |
| `--collation-server=utf8mb4_unicode_ci` | Case-insensitive matching on Filipino names, which is what users expect |
| `redis` on **one** container | Both the channel layer (db 0) and the cache (db 1) use this one instance. Two Redis containers would double the moving parts for no benefit |

Compose reads `.env` automatically from the same folder, so `MYSQL_PASSWORD` comes
from your real `.env` — the `:-sakayph` defaults are only a fallback for a fresh
clone that has no `.env` yet.

**Port conflict check.** This machine already runs a native MySQL 8.4 service
(`MySQL84`) on port 3306, so the mapping above publishes the container on **3307**,
and `.env` and `.env.example` both carry `MYSQL_PORT=3307`. If `up` still fails with
*"port is already allocated"*, confirm with
`Get-NetTCPConnection -LocalPort 3307 -State Listen` and remap to `"3308:3306"` —
changing `MYSQL_PORT` in **both** env files to match.

### 3. Start the services and prove they are healthy (~15 min)

```powershell
docker compose up -d
```

Then:

```powershell
docker compose ps
```

Both services should show `Up` and, after ~30 seconds, `healthy`. MySQL takes
longer than Redis on first start because it initialises the data directory.

**Prove the database is actually usable, not just running:**

```powershell
docker compose exec mysql mysql -u root -prootpw -e "SHOW DATABASES; SHOW VARIABLES LIKE 'character_set_server';"
```

Expected: `sakayph` appears in the list, and `character_set_server` is `utf8mb4`.
If it says `latin1`, the `command:` block did not apply — the volume was created by
an earlier run with different settings. Fix with `docker compose down -v` (this
wipes the volume) then `up -d` again.

**Prove Redis is reachable:**

```powershell
docker compose exec redis redis-cli ping
```

Expected: `PONG`.

> **Persistence check.** Stop and start once to confirm data survives:
> `docker compose down` then `docker compose up -d`. `down` without `-v` keeps the
> named volumes. `down -v` deletes them. Knowing which is which now prevents an
> accidental database wipe in Phase 2.

### 4. Create the Python environment and requirements (~30 min)

```powershell
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked by execution policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

You should now see `(.venv)` at the start of your prompt. **Every command from here
to the end of this step runs inside the virtual environment.**

Create the requirements folder:

```powershell
New-Item -ItemType Directory -Force requirements | Out-Null
```

Write `requirements/base.txt`:

```text
# ── Sakay.ph runtime dependencies ──────────────────────────────
# Pinned exactly. A capstone graded on reproducibility should
# install the same versions on the assessor's machine.

# ── Core ───────────────────────────────────────────────────────
Django==6.1.3
djangorestframework==3.18.3
djangorestframework-simplejwt==5.5.1
django-cors-headers==4.9.0
drf-spectacular==0.30.0
django-environ==0.14.0

# ── Database ───────────────────────────────────────────────────
# PyMySQL rather than mysqlclient: pure Python, no C compiler or
# MySQL client libraries needed on Windows. The [rsa] extra adds
# the auth plugin MySQL 8.4 requires.
PyMySQL[rsa]==1.2.3

# ── Real-time ──────────────────────────────────────────────────
channels==4.3.2
channels-redis==4.3.0
django-redis==6.0.0
daphne==4.2.1

# ── Geospatial ─────────────────────────────────────────────────
geopy==2.4.1
```

Write `requirements/dev.txt`:

```text
# ── Development and testing ────────────────────────────────────
-r base.txt

pytest==9.0.1
pytest-django==4.12.0
pytest-cov==7.1.0
factory-boy==3.3.3
ruff==0.15.1
```

> **Do not trust those pins blindly — verify them.** They come from the stack
> document, which was written from release notes, not from an install. The versions
> of `channels-redis`, `django-redis`, `daphne`, `geopy`, and everything in
> `dev.txt` were not confirmed against PyPI. Run the install; if pip says
> *"No matching distribution found"*, you have found a real defect and you should
> record it (see "If it goes wrong").

Install:

```powershell
python -m pip install --upgrade pip
pip install -r requirements/dev.txt
```

**Capture the exact output.** This is the evidence for stack doc §7:

```powershell
pip install -r requirements/dev.txt 2>&1 | Tee-Object -FilePath docs\plan\install-log.txt
```

If that pin set fails, the fallback is to install unpinned, find what actually
resolves, then pin to that:

```powershell
pip install Django djangorestframework djangorestframework-simplejwt django-cors-headers drf-spectacular django-environ "PyMySQL[rsa]" channels channels-redis django-redis daphne geopy
pip freeze
```

Take the versions from `pip freeze`, put them in `requirements/base.txt`, and note
in the install log that the stack document's pins were wrong and what they became.

**The single most likely failure:** `cryptography`, pulled in by `PyMySQL[rsa]`,
may have no prebuilt wheel for Python 3.14 on Windows and will try to build from
source — which needs Rust. If you see *"error: can't find Rust compiler"*, the fix
is either `pip install --only-binary=:all: "PyMySQL[rsa]"` to force a wheel, or
`winget install Rustlang.Rustup`. Record which one you needed.

### 5. Configure PyMySQL as the MySQL driver (~10 min)

Django's MySQL backend imports `MySQLdb`. PyMySQL provides it under a different
name, so it needs a shim. Add this to `backend/config/__init__.py` **after** step 6
creates it — or create the file now if you prefer:

```python
# backend/config/__init__.py
"""Sakay.ph Django project package.

PyMySQL is installed instead of mysqlclient, so it must be registered
under the name Django's MySQL backend expects. This must run before any
Django app loads a database connection.
"""

import pymysql

pymysql.install_as_MySQLdb()
```

This is worth understanding rather than copy-pasting: `install_as_MySQLdb()` does
nothing more than register `pymysql` in `sys.modules` under the key `MySQLdb`, so
Django's `import MySQLdb` finds it. Without this file you get
`django.core.exceptions.ImproperlyConfigured: Error loading MySQLdb module`.

### 6. Scaffold the Django project (~20 min)

`backend/` currently holds only a `.gitkeep`. Django's `startproject` will happily
write into it.

```powershell
Set-Location backend
django-admin startproject config .
Set-Location ..
```

The trailing `.` matters: it puts `manage.py` at `backend/manage.py` and the
settings package at `backend/config/`, rather than nesting a second `backend/`
folder inside the first.

Expected result:

```
backend/
├── .gitkeep          ← delete this now; real files exist
├── config/
│   ├── __init__.py   ← put the PyMySQL shim here
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── manage.py
```

```powershell
Remove-Item backend\.gitkeep
```

**Prove Django starts before you configure anything.** A scaffold that does not run
means the problem is the install, and it is much easier to diagnose now than after
you have added settings:

```powershell
Set-Location backend
python manage.py runserver
```

Open `http://127.0.0.1:8000` — you should see the Django rocket. Then `Ctrl+C`.

Leave `settings.py` at its defaults for now. Phase 2 (step 2.02) rewrites it
properly: `django-environ`, MySQL, Channels, CORS, DRF, SimpleJWT. Doing it here
would mean doing it twice.

### 7. Scaffold the Vue frontend (~30 min)

`frontend/` holds only a `.gitkeep`, and `create-vue` refuses to write into a
non-empty directory without prompting. Remove the placeholder first:

```powershell
Remove-Item -Recurse -Force frontend
npm create vue@latest frontend
```

Answer the prompts:

| Prompt | Answer | Why |
|---|---|---|
| TypeScript? | **No** | The stack is JavaScript. Adding TS mid-project costs time for no rubric benefit |
| JSX? | No | Not used |
| Vue Router? | **Yes** | Required — role-based routes for passenger vs driver |
| Pinia? | **Yes** | Required — auth and ride state |
| Vitest? | **Yes** | Phase 5 needs a frontend test |
| E2E (Playwright/Cypress)? | **No** | Out of scope for 31 days |
| ESLint? | **Yes** | Graded as process evidence |
| Prettier? | **Yes** | Same |

Then:

```powershell
Set-Location frontend
npm install
npm install axios leaflet
npm install -D tailwindcss @tailwindcss/vite
Set-Location ..
```

> **Tailwind 4 has no `tailwind.config.js` and no PostCSS config.** It is a Vite
> plugin. If you follow a Tailwind 3 tutorial here you will create files that do
> nothing. Wiring it into `vite.config.js` is Phase 4's job — installing it now
> proves the package resolves.

**Prove the frontend starts:**

```powershell
Set-Location frontend
npm run dev
```

Open the printed URL (usually `http://127.0.0.1:5173`). You should see the Vue
starter page. Then `Ctrl+C`.

### 8. Prove both servers run at once (~15 min)

This is the real test, and it is the one people skip. Two terminals:

```powershell
# Terminal 1 — backend
Set-Location backend
..\.venv\Scripts\Activate.ps1
python manage.py runserver

# Terminal 2 — frontend
Set-Location frontend
npm run dev
```

Both must serve simultaneously. They use different ports (8000 and 5173), so they
do not conflict — but a wrong `VITE_API_BASE_URL` or a stray `PORT` variable would
show up here rather than in Phase 4.

### 9. Record the evidence (~15 min)

Append the tool versions, the install output, and any deviations to
`docs/plan/install-log.txt`. This file is deliberately **not** git-ignored — it is
the proof behind stack doc §7's "verified on" column.

Then update `docs/proposal/technology_stack.md` §7:

| Package | Pinned | Verified on this machine | Notes |
|---|---|---|---|
| Django | 6.1.3 | ☐ | |
| … | … | ☐ | |

Tick each box that installed at the pinned version. Any box you cannot tick gets a
note explaining what it became instead. **An unverified row that says so is worth
more than a verified row that is not true.**

### 10. Commit (~10 min)

The `.venv/` and `node_modules/` folders are already ignored by Step 1.02. Confirm
before committing — this is the commit where a stray ignore failure would hurt most:

```powershell
git status --short
```

`.venv/`, `node_modules/`, and `dist/` must **not** appear. Then:

```powershell
git add docker-compose.yml requirements/ backend/ frontend/ docs/plan/install-log.txt
git commit -m "chore(repo): scaffold Django and Vue, add docker compose and pinned requirements"
git push
```

---

## Verify

```powershell
# Services healthy
docker compose ps

# Database reachable with the right encoding
docker compose exec mysql mysql -u root -prootpw -e "SHOW VARIABLES LIKE 'character_set_server';"

# Redis reachable
docker compose exec redis redis-cli ping

# Django imports its settings without error
Set-Location backend
python -c "import django; print(django.get_version())"
python manage.py check
Set-Location ..

# Frontend installed
Test-Path frontend\node_modules\vue
Test-Path frontend\package.json
```

- [ ] `docker compose ps` shows MySQL and Redis both `Up`, ideally `healthy`
- [ ] `character_set_server` is `utf8mb4`
- [ ] `redis-cli ping` returns `PONG`
- [ ] `python manage.py check` reports no errors
- [ ] `python manage.py runserver` serves the Django welcome page on :8000
- [ ] `npm run dev` serves the Vue starter page on :5173
- [ ] Both run **at the same time**
- [ ] `.venv/` and `node_modules/` are absent from `git status`
- [ ] `docs/plan/install-log.txt` exists and holds the real install output
- [ ] Stack doc §7 has a verified/unverified mark on every row
- [ ] Committed and pushed

---

## Log it

```markdown
**Step 1.06 — scaffold and verify — DONE**

- Docker Compose: MySQL 8.4 + Redis 7 both healthy; utf8mb4 confirmed on the server
- requirements/base.txt and dev.txt pinned and installed; install log captured
- Django 6.1.3 scaffolded at backend/ (config project); PyMySQL shim in place
- Vue scaffolded at frontend/ with Router, Pinia, Vitest, ESLint, Prettier, Tailwind 4
- Both servers verified running simultaneously (8000 + 5173)
- **Deviations from the stack doc:** <none | list>
- **Commit:** <sha>
```

Then:

- Set the **install-log column** in `docs/plan/design-freeze.md`
- Close risks **R2, R3, R4, R6** in the roadmap's risk register, or downgrade them
  with a note on what actually happened
- Add a decision-log row if any pin changed

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `docker: command not found` | Docker Desktop not installed | `winget install --id Docker.DockerDesktop`, then reboot |
| `error during connect` / `cannot connect to the Docker daemon` | Docker Desktop installed but not started | Launch Docker Desktop, wait for the whale to settle |
| `port is already allocated` | A native MySQL/Redis already owns 3307 or 6379 | Confirm with `Get-NetTCPConnection -LocalPort 3307,6379 -State Listen`, then remap to `3308:3306` and update `MYSQL_PORT` in **both** `.env` and `.env.example` |
| `character_set_server` is `latin1` | Volume predates the `command:` block | `docker compose down -v` (wipes data), then `up -d` |
| `No matching distribution found for <pkg>==<ver>` | A pin in the stack doc was wrong | Install unpinned, `pip freeze`, re-pin to what resolved. **Record it** — this is a real finding |
| `error: can't find Rust compiler` | `cryptography` has no Python 3.14 wheel | `pip install --only-binary=:all: "PyMySQL[rsa]"`, or `winget install Rustlang.Rustup` |
| `Error loading MySQLdb module` | The PyMySQL shim is missing or misplaced | `backend/config/__init__.py` must call `pymysql.install_as_MySQLdb()` before Django loads |
| `.\.venv\Scripts\Activate.ps1` is blocked | PowerShell execution policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `create-vue` asks to overwrite `frontend/` | The `.gitkeep` makes it non-empty | `Remove-Item -Recurse -Force frontend` first |
| `npm run dev` fails on Node 24 | Vite/Node mismatch (R4) | Check the error. Usually a Vite minor bump fixes it — record the version change |
| Django 6.1 breaks `channels` on import | R3, a genuine incompatibility | This is the finding this step exists to produce. Report it — the fallback is pinning Django to the last version Channels supports |
| `pip install` output is enormous | Normal | That is why it goes to a file, not the console |

---

## After this step

**Phase 1 is complete and milestone M1 is met.** The evidence:

- A public repository a stranger can clone and understand
- A frozen, self-consistent design with a completed stack document
- A working development environment, verified rather than assumed
- A commit history that reads as a process

```powershell
git log --oneline
git tag -a v0.1.0-dev -m "Design frozen, repository live, environment verified"
git push origin v0.1.0-dev
```

> **This is not the `v0.1.0` tag.** `CONTRIBUTING.md` reserves that for the end of
> Phase 2, when the database is real. This one marks M1 and is a development tag.

Next: **Phase 2 — Database and Domain Model**, starting with
[00 — Overview](../phase-2-database/00-overview.md). That phase turns the 27-table
schema from a document into migrations, and it is the largest single phase in the
project.
