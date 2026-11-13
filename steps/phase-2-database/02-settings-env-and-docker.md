# Step 2.02 — Settings, Environment and Database Connection

| | |
|---|---|
| **Goal** | `settings.py` reads every secret from `.env`; Django connects to MySQL 8.4 and round-trips a Tagalog string with emoji without corrupting it |
| **Day / Time** | Day 9 (Sat 14 Nov) · ~2 hours |
| **Prerequisites** | [Step 2.01](01-apps-and-shared-conventions.md); Docker services running from [Step 1.06](../phase-1-repository/06-scaffold-and-verify.md) |
| **Produces** | A configured `backend/config/settings.py` and a proven database connection |

---

## Why the connection test is not "run migrate and see"

Because `migrate` succeeding does not prove the connection is *correct*. Two failures
pass a naive test and only surface weeks later:

| Failure | Looks fine because | Actually broken because |
|---|---|---|
| `latin1` collation | Migrations create tables successfully | A barangay name with `ñ` is stored as `?`, and you find out in Phase 4 |
| Wrong timezone handling | Rows insert | `request_time` drifts by 8 hours, and every "how long did this ride take" figure is wrong |

So the verification in this step does three specific things: it prints the server's
character set, it round-trips a string containing `ñ` and an emoji, and it checks
what timezone Django thinks it is in.

---

## Do this

### 1. Confirm the services are up (~5 min)

```powershell
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem"
docker compose ps
```

Both `sakayph-mysql` and `sakayph-redis` must be `Up`. If not:

```powershell
docker compose up -d
```

### 2. Confirm `.env` has real values (~5 min)

```powershell
Get-Content .env
```

Check that `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD` match what `docker-compose.yml`
passed to the container. The compose file reads `.env` too, so they agree by
construction — but only if you edited `.env` **before** the first `docker compose up`.
If you started the container first and edited `.env` after, the MySQL user still has
the old password.

**If you are unsure, reset the database volume.** There is no data yet, so this costs
nothing:

```powershell
docker compose down -v
docker compose up -d
```

Wait ~30 seconds for MySQL to initialise, then `docker compose ps` until it is
`healthy`.

### 3. Write `settings.py` (~60 min)

Replace the contents of `backend/config/settings.py`. Read the comments — several of
these settings are not defaults, and each one has a reason.

```python
# backend/config/settings.py
"""Django settings for the Sakay.ph backend.

Every secret and every environment-specific value is read from `.env` via
django-environ. Nothing in this file should need to change between a
developer machine and the submission build.
"""

from datetime import timedelta
from pathlib import Path

import environ

# ── Paths ──────────────────────────────────────────────────────
# settings.py is at backend/config/settings.py, so BASE_DIR is backend/.
BASE_DIR = Path(__file__).resolve().parent.parent
# The repository root, one level above backend/.
ROOT_DIR = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_TIME_ZONE=(str, "Asia/Manila"),
    # Host port published by docker-compose.yml (3307:3306) — a native MySQL 8.4
    # service already owns host port 3306 on the development machine.
    MYSQL_PORT=(int, 3307),
    SIMULATE_PAYMENTS=(bool, True),
    SIMULATE_OTP=(bool, True),
    OTP_TTL_SECONDS=(int, 300),
)

# Read the repository-root .env, not one inside backend/.
environ.Env.read_env(ROOT_DIR / ".env")

# ── Core ───────────────────────────────────────────────────────
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# ── Applications ───────────────────────────────────────────────
INSTALLED_APPS = [
    "daphne",  # must precede staticfiles so runserver uses ASGI

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "channels",

    "apps.core",
    "apps.accounts",
    "apps.rides",
    "apps.payments",
    "apps.safety",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must precede CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ── Database ───────────────────────────────────────────────────
# PyMySQL is registered as MySQLdb in config/__init__.py — see Step 1.06.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("MYSQL_DATABASE"),
        "USER": env("MYSQL_USER"),
        "PASSWORD": env("MYSQL_PASSWORD"),
        "HOST": env("MYSQL_HOST"),
        "PORT": env("MYSQL_PORT"),
        "OPTIONS": {
            # utf8mb4 end to end. Tagalog diacritics and the emoji transport
            # icons both need 4-byte UTF-8; utf8mb3 silently truncates them.
            "charset": "utf8mb4",
            # Fail loudly on a strict-mode violation rather than silently
            # truncating a value that is too long for its column.
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "CONN_MAX_AGE": 60,
        "TEST": {
            "NAME": "test_sakayph",
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_unicode_ci",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Passwords ──────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ───────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE")
USE_I18N = True
# Store UTC, display Asia/Manila. Turning this off is the classic source of
# an eight-hour error in every duration the app reports.
USE_TZ = True

# ── Static and media ───────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── Django REST Framework ──────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,  # token_blacklist app is not installed
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sakay.ph API",
    "DESCRIPTION": (
        "Isang App, Lahat ng Sakyan. Multi-mode ride-hailing for the Philippines. "
        "CCS670 capstone."
    ),
    "VERSION": "0.2.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ── CORS ───────────────────────────────────────────────────────
# The Vite dev server is a different origin from Django, so without this
# every request from the frontend fails in the browser.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# ── Channels and Redis ─────────────────────────────────────────
# One Redis container, two logical databases: db 0 for the channel layer,
# db 1 for the cache. They are separated so a cache flush cannot drop a
# live WebSocket group.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL")],
        },
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "sakayph",
    }
}

# ── Application flags ──────────────────────────────────────────
SIMULATE_PAYMENTS = env("SIMULATE_PAYMENTS")
SIMULATE_OTP = env("SIMULATE_OTP")
OTP_TTL_SECONDS = env("OTP_TTL_SECONDS")

# ── Logging ────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        # Set to DEBUG when a WebSocket will not connect.
        "django.channels": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
```

**Five settings in there are not defaults, and each is load-bearing:**

| Setting | Why |
|---|---|
| `"daphne"` first in `INSTALLED_APPS` | It replaces `runserver` with the ASGI server, so WebSockets work in development without a second process |
| `charset: utf8mb4` in `OPTIONS` | The connection charset, separate from the server's. Both must be right |
| `init_command: STRICT_TRANS_TABLES` | Without it MySQL truncates an over-long value with a warning instead of erroring — a silent data-loss bug |
| `USE_TZ = True` | Store UTC, display Manila time |
| `CORS_ALLOWED_ORIGINS` | Without it the browser blocks every Phase 4 request, and the error appears in the browser console, not the Django log |

### 4. Confirm the PyMySQL shim is in place (~5 min)

`backend/config/__init__.py` must contain the shim from Step 1.06:

```python
import pymysql

pymysql.install_as_MySQLdb()
```

Without it you get `ImproperlyConfigured: Error loading MySQLdb module`. This is the
single most common failure in this step.

### 5. Prove the connection (~20 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
python manage.py check
```

Expected: no issues. **Do not run `migrate` yet** — the models are not written, and
migrating now only creates Django's own tables.

Now the connection test:

```powershell
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('vendor:', connection.vendor); print('server:', connection.mysql_version)"
```

Expected:

```
vendor: mysql
server: (8, 4, ...)
```

### 6. Prove the encoding is actually utf8mb4 (~20 min)

This is the test that matters. Run it in `manage.py shell`:

```powershell
python manage.py shell
```

```python
from django.db import connection

with connection.cursor() as cur:
    # 1. What charset is the *connection* using?
    cur.execute("SHOW VARIABLES LIKE 'character_set_%'")
    for row in cur.fetchall():
        print(row)

    # 2. What charset is the *server* using?
    cur.execute("SHOW VARIABLES LIKE 'collation_server'")
    print(cur.fetchall())

    # 3. Round-trip the characters that actually break.
    #    ñ        — Spanish-derived Filipino place names (Peñaflor, Muñoz)
    #    ₱        — the peso sign
    #    🚐 🛺    — the mode icons in the UI
    cur.execute("CREATE TEMPORARY TABLE _enc_test (s VARCHAR(100)) "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    probe = "Barangay Peñaflor ₱25.00 🚐🛺"
    cur.execute("INSERT INTO _enc_test (s) VALUES (%s)", [probe])
    cur.execute("SELECT s FROM _enc_test")
    got = cur.fetchone()[0]
    print("sent:", repr(probe))
    print("got :", repr(got))
    print("MATCH" if got == probe else "*** CORRUPTED ***")
```

Expected: `character_set_client`, `character_set_connection` and
`character_set_results` are all `utf8mb4`, and the last line prints **MATCH**.

If it prints `*** CORRUPTED ***` or shows `?` characters, stop and fix it now:

| Where it is wrong | Fix |
|---|---|
| `character_set_connection` is `latin1` | The `charset` in `DATABASES["default"]["OPTIONS"]` is not applying |
| `collation_server` is `latin1_swedish_ci` | The MySQL container was created without the `command:` block. `docker compose down -v` then `up -d` |
| Only the emoji break, not the `ñ` | You are on `utf8mb3`, which is 3-byte. Everything must be `utf8mb4` |

Then exit with `exit()`.

### 7. Prove Redis works through both paths (~15 min)

```powershell
python manage.py shell
```

```python
# Cache path — django-redis, db 1
from django.core.cache import cache
cache.set("probe", "kumusta", 30)
print("cache:", cache.get("probe"))

# Channel layer path — channels_redis, db 0
import asyncio
from channels.layers import get_channel_layer

async def probe():
    layer = get_channel_layer()
    await layer.send("probe-group", {"type": "probe.message", "text": "kumusta"})

asyncio.run(probe())
print("channel layer: sent without error")
```

Expected: `cache: kumusta` and a clean send. A `ConnectionRefusedError` means the
Redis container is not running.

Then `exit()`.

### 8. Confirm `.env` is still ignored (~5 min)

You have just added settings that read secrets. Make sure nothing leaked:

```powershell
Set-Location ..
git status --short
```

`.env` must not appear. Then commit:

```powershell
git add backend/config/ apps/ requirements/
git commit -m "feat(config): wire settings to env, MySQL 8.4, Redis, DRF and Channels"
git push
```

---

## Verify

- [ ] `docker compose ps` shows both services `Up`
- [ ] `python manage.py check` reports no issues
- [ ] `connection.vendor` is `mysql` and the version is 8.4.x
- [ ] `character_set_client`, `_connection`, `_results` are all `utf8mb4`
- [ ] `collation_server` is `utf8mb4_unicode_ci`
- [ ] The `Peñaflor ₱25.00 🚐🛺` round-trip prints **MATCH**
- [ ] `cache.get("probe")` returns `kumusta`
- [ ] The channel-layer send completes without error
- [ ] `.env` is absent from `git status`
- [ ] Committed and pushed

---

## Log it

```markdown
**Step 2.02 — settings, env and database connection — DONE**

- settings.py reads .env via django-environ; no secret in source
- MySQL 8.4 connection proven: vendor=mysql, version=8.4.x
- utf8mb4 verified on connection, server and collation; Peñaflor ₱ 🚐 round-trip MATCH
- Redis verified on both paths: django-redis cache (db 1) and channels_redis (db 0)
- TIME_ZONE=Asia/Manila, USE_TZ=True (store UTC, display Manila)
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `ImproperlyConfigured: Error loading MySQLdb module` | PyMySQL shim missing | Add `pymysql.install_as_MySQLdb()` to `backend/config/__init__.py` |
| `Access denied for user 'sakayph'@'%'` | `.env` password differs from what the container was created with | `docker compose down -v && docker compose up -d` — the container only reads `.env` at creation |
| `Can't connect to MySQL server on '127.0.0.1'` | Container not running, or still initialising | `docker compose ps`, wait for `healthy` |
| `Unknown database 'sakayph'` | `MYSQL_DATABASE` in `.env` differs from the container's | Reset the volume as above |
| `environ.ImproperlyConfigured: Set the DJANGO_SECRET_KEY` | `.env` not found at the repo root | `ROOT_DIR / ".env"` — confirm the path is `backend/../.env` |
| `No module named 'daphne'` | Not installed | `pip install -r requirements/dev.txt` |
| `redis.exceptions.ConnectionError` | Redis container down | `docker compose up -d redis` |
| Emoji corrupted but `ñ` fine | `utf8mb3` somewhere | Check all three `character_set_*` variables |
| `check` complains about `AUTH_USER_MODEL` | Expected — it is set in Step 03 | Ignore for now |

---

## After this step

Django can talk to MySQL and Redis. There are still no application tables — the
models land next, starting with the people: users, drivers, vehicles and LGU
accreditation.

Next: [03 — Models: accounts](03-models-accounts.md)
