# Step 1.01 — Initialise Git and the Folder Structure

| | |
|---|---|
| **Goal** | Git is initialised on branch `main` in the project root, and the folders the build will use exist |
| **Day / Time** | Day 6 (Wed 11 Nov) · ~30 min |
| **Prerequisites** | [Phase 0](../phase-0-design-completion/00-overview.md) complete |
| **Produces** | `.git/`, `backend/`, `frontend/`, `tools/` |

---

## Do this

### 1. Confirm git is present and identified (~5 min)

```powershell
git --version
git config --global user.name
git config --global user.email
```

If either config line prints nothing, set them — every commit needs them:

```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

Use the same email as your GitHub account, or the commits will not be attributed to
you on the repository page.

### 2. Move to the project root and initialise (~5 min)

```powershell
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem"
git init
git branch -M main
```

`git branch -M main` renames the default branch. Do this **now**, before the first
commit — renaming afterwards is possible but pointless churn in the history.

```powershell
git status
```

Expect every existing file listed as untracked. That is correct; nothing is
committed yet.

### 3. Create the build folders (~10 min)

```powershell
New-Item -ItemType Directory -Force backend, frontend, tools | Out-Null
New-Item -ItemType File -Force backend\.gitkeep, frontend\.gitkeep, tools\.gitkeep | Out-Null
```

**Why `.gitkeep`:** git does not track empty directories. Without these files the
folders vanish on clone, and `docker compose` or a build script referencing
`backend/` fails on a fresh checkout. They get deleted in Phase 2 and Phase 4 when
real files land.

### 4. Confirm the structure (~5 min)

```powershell
Get-ChildItem -Force | Select-Object Mode, Name
```

Expected at the root:

```
.git/
backend/
database/
docs/
frontend/
steps/
tools/
README.md          (from Step 0.02)
```

> **`database/` stays at the root.** Audit finding A-12 explains why: roughly thirty
> path references in `consistency_report.md` and `schema_listing.md` point at
> `database/...`. Moving it for tidiness would invalidate every one. The root README
> documents the layout instead.

---

## Verify

```powershell
# On the main branch, nothing committed yet
git branch --show-current          # → main

# The folders exist and are non-empty
Test-Path backend\.gitkeep         # → True
Test-Path frontend\.gitkeep        # → True
Test-Path tools\.gitkeep           # → True

# Git sees the design artefacts as untracked
git status --short | Measure-Object -Line
```

- [ ] `git branch --show-current` prints `main`
- [ ] `backend/`, `frontend/`, `tools/` all exist
- [ ] `.gitkeep` present in **all three** — an empty folder with no placeholder does
      not survive a clone
- [ ] `git status` lists the existing 65 files as untracked

---

## Log it

```markdown
**Step 1.01 — git init and folder structure — DONE**

- `git init` on branch `main`; user.name/user.email confirmed set
- Created backend/, frontend/, tools/ with .gitkeep placeholders
- database/ left at root (A-12 — ~30 path references depend on it)
- **Commit:** (folded into Step 1.04's first push)
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `git` not recognised | Git not installed or not on PATH | Install from git-scm.com, reopen the terminal |
| Branch is `master` not `main` | Older git default | `git branch -M main` — harmless if already `main` |
| `.gitkeep` files not visible | Hidden-dot files | `Get-ChildItem -Force` shows them |
| Already ran `git init` in a parent folder | Common mistake | `Remove-Item -Recurse -Force .git` at the parent, then re-init here. Check with `git rev-parse --show-toplevel` |
