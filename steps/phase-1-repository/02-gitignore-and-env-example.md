# Step 1.02 — Write `.gitignore` and `.env.example`

| | |
|---|---|
| **Goal** | Secrets and build artefacts can never be committed by accident, and the environment is documented |
| **Day / Time** | Day 6 (Wed 11 Nov) · ~30 min |
| **Prerequisites** | [Step 1.01](01-git-init-and-structure.md) |
| **Produces** | `.gitignore`, `.env.example` |

---

## Do this

### 1. Write `.gitignore` at the project root (~20 min)

Create `.gitignore` with this content:

```gitignore
# ── Secrets ────────────────────────────────────────────────────
# NEVER commit these. If one is ever committed, it is in the history
# forever — rotating the credential is the only real fix.
.env
.env.*
!.env.example
*.pem
*.key

# ── Python ─────────────────────────────────────────────────────
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
env/
ENV/
*.egg-info/
dist/
build/

# ── Django ─────────────────────────────────────────────────────
*.log
db.sqlite3
db.sqlite3-journal
/media/
/staticfiles/
backend/staticfiles/

# ── Testing & coverage ─────────────────────────────────────────
.pytest_cache/
.coverage
.coverage.*
htmlcov/
coverage.xml
*.cover

# ── Linting caches ─────────────────────────────────────────────
.ruff_cache/
.mypy_cache/

# ── Node / Vue ─────────────────────────────────────────────────
node_modules/
dist/
dist-ssr/
.vite/
*.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*

# ── Editors ────────────────────────────────────────────────────
.vscode/*
!.vscode/extensions.json
!.vscode/settings.json
.idea/
*.swp

# ── OS ─────────────────────────────────────────────────────────
Thumbs.db
Desktop.ini
.DS_Store

# ── Docker ─────────────────────────────────────────────────────
# Named volumes live inside Docker, but a local bind-mount folder
# would land here if one is added later.
mysql_data/
redis_data/
```

**What is deliberately NOT ignored:**

| Not ignored | Why |
|---|---|
| `docs/**/*.png` | The diagram renders and mockups are deliverables — they must be committed |
| `docs/plan/install-log.txt` | Phase 1 install output is evidence for stack doc §7 |
| `.vscode/settings.json` | Shared editor settings help a reader reproduce the environment |
| `*.puml` | Source for the diagrams; committing them makes the design reproducible |

### 2. Write `.env.example` (~10 min)

This is the template that **is** committed. It documents every environment variable
the app reads, with placeholder values — never real ones.

```dotenv
# ── Sakay.ph environment template ──────────────────────────────
# Copy to `.env` and fill in real values:
#     Copy-Item .env.example .env
# `.env` is git-ignored. This file is not. Never put a real secret here.

# ── Django ─────────────────────────────────────────────────────
DJANGO_SECRET_KEY=replace-me-with-a-long-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_TIME_ZONE=Asia/Manila

# ── Database (MySQL 8.4, via Docker Compose) ───────────────────
MYSQL_DATABASE=sakayph
MYSQL_USER=sakayph
MYSQL_PASSWORD=replace-me
MYSQL_ROOT_PASSWORD=replace-me-too
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306

# ── Redis (via Docker Compose) ─────────────────────────────────
# db 0 = Django Channels channel layer
# db 1 = Django cache
REDIS_URL=redis://127.0.0.1:6379/0
REDIS_CACHE_URL=redis://127.0.0.1:6379/1

# ── Frontend ───────────────────────────────────────────────────
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_WS_BASE_URL=ws://127.0.0.1:8000/ws

# ── Simulated providers ────────────────────────────────────────
# No real payment gateway, SMS gateway, or GPS hardware is used.
# These flags keep the simulations honest and visible.
SIMULATE_PAYMENTS=True
SIMULATE_OTP=True
OTP_TTL_SECONDS=300
```

> **`VITE_` is not decoration.** Vite only exposes environment variables to the
> browser bundle if they start with `VITE_`. Without the prefix the variable is
> `undefined` in the frontend and you will debug it for an hour.

### 3. Create your local `.env` (~5 min)

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and replace every `replace-me` value. For `DJANGO_SECRET_KEY`:

```powershell
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

If Django is not installed yet, any long random string will do for now.

### 4. Prove the ignore rules work (~5 min)

**This is the step that matters.** Do not skip it.

```powershell
git status --short
```

`.env` must **not** appear. `.env.example` **must** appear. If `.env` shows up, the
pattern is wrong — fix `.gitignore` before going any further.

```powershell
git check-ignore -v .env
```

Expected: a line naming the `.gitignore` pattern that matched. If it prints nothing,
`.env` is not ignored.

---

## Verify

- [ ] `.gitignore` exists at the root
- [ ] `.env.example` exists at the root
- [ ] `.env` exists locally and is **not** listed by `git status`
- [ ] `git check-ignore -v .env` names the matching pattern
- [ ] `.env.example` **is** listed by `git status` as untracked

---

## Log it

```markdown
**Step 1.02 — .gitignore and .env.example — DONE**

- Wrote .gitignore (secrets, Python, Django, Node, editors, OS)
- Deliberately kept docs PNGs and *.puml tracked — they are deliverables
- Wrote .env.example documenting all vars; created local .env from it
- Verified with `git check-ignore -v .env` — .env ignored, .env.example tracked
- **Commit:** (folded into Step 1.04's first push)
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `.env` appears in `git status` | Pattern missing or misspelled | `git check-ignore -v .env` to see which pattern (if any) matched |
| `.env.example` is ignored too | `.env.*` is catching it | The `!.env.example` negation must come **after** `.env.*` — order matters in `.gitignore` |
| Already committed `.env` | You committed before writing the ignore | `git rm --cached .env`, then commit. **Also rotate the password** — it is in the history |
| `node_modules` shows as untracked | Pattern not applied | Confirm `.gitignore` is at the repository root, not inside `frontend/` |

---

## A note on why this step is not optional

The most common serious finding in a student project is a committed credential. It
happens because `.gitignore` is written *after* the first commit, when the file is
already tracked — and once tracked, `.gitignore` does not help; the file stays
tracked until explicitly removed.

You are writing this file **before** any `.env` exists. That is the correct order,
and it costs nothing now versus a history rewrite later.
