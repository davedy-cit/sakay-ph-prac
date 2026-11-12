# Phase 1 — Repository

**Days 6–7 · 11–12 November 2026**
**Time budget: about 1.5 days**

---

## Goal

The project exists on GitHub with a complete history, a working environment, and
both application scaffolds in place — so that Phase 2 starts writing models on an
empty but *proven* foundation.

---

## Why this phase comes before any code

Audit finding **A-03**: there is no repository, no `.gitignore`, and no README.
Nothing is under version control.

Three reasons this is not a formality:

1. **Process evidence is graded.** CCS670 assesses software development, not just
   software. A clean commit history from Day 6 to Day 31 is direct evidence that
   you worked through a process. A single "initial commit" on Day 30 is evidence of
   the opposite.
2. **Recovery.** You will break something. Without version control, "it worked
   yesterday" is not recoverable.
3. **The environment is the risk.** Audit risks R2, R3, R4 and R6 are all
   *install-time* risks: version pins that may not resolve, a Python 3.14 wheel that
   may not exist, Docker/Redis on Windows, Channels against Django 6.1. Every one of
   them surfaces on **Day 7** if you install now, and on Day 25 if you install later.
   Finding them today costs an afternoon. Finding them in three weeks costs the
   project.

---

## Steps

| | Step | Day | What exists when it's done |
|---|---|---|---|
| ⬜ | [01 — Initialise git and the folder structure](01-git-init-and-structure.md) | 6 | `git init` on branch `main`; `backend/`, `frontend/`, `tools/` created; `.gitkeep` files in place |
| ⬜ | [02 — Write `.gitignore` and `.env.example`](02-gitignore-and-env-example.md) | 6 | Secrets can never be committed by accident; the environment is documented |
| ⬜ | [03 — Create the GitHub repository](03-github-repo.md) | 6 | An empty remote repository exists, correctly named and licensed |
| ⬜ | [04 — First push](04-first-push.md) | 6 | All 65 design and process files are on GitHub with a clean history |
| ⬜ | [05 — Workflow conventions](05-workflow-conventions.md) | 7 | Commit, branch and tag conventions recorded in `CONTRIBUTING.md` |
| ⬜ | [06 — Scaffold Django and Vue, prove the environment](06-scaffold-and-verify.md) | 7 | `docker compose up` starts MySQL + Redis; both scaffolds install clean; `runserver` and `npm run dev` both serve |

---

## Milestone M1 exit criterion

> A stranger can clone the repository, read the README, and understand the project
> without asking you anything.

That is the bar. Not "the code works" — no code exists yet. It is that the
repository is **self-explanatory**.

---

## The one decision to make here

**One repository or two?** This plan uses **one repository, two apps**
(`backend/` + `frontend/`).

The alternative — separate repositories — would give you two commit histories, two
READMEs, two submission links, and a version-compatibility problem the moment an
API change and a UI change need to land together. For a solo capstone, one
repository is simply less to manage, and it matches how the project is submitted:
one link.

---

## Watch out for

**Do not commit the `.env` file.** Step 02 exists specifically to prevent this. A
committed database password is a real security finding in a graded project — and
since the password will be in your history forever, fixing it later means rewriting
history, which you do not want to be doing on Day 30.

**Do not skip Step 06.** It is the least interesting step in this phase and the
most valuable. It is where the version risks get caught.

---

## Next

**Phase 2 — Database** · Days 8–14 · [../phase-2-database/00-overview.md](../phase-2-database/00-overview.md)
