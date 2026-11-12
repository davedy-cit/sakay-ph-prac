# Step 1.05 — Workflow Conventions

| | |
|---|---|
| **Goal** | The rules for commits, branches and tags are written down once, so you never have to think about them again |
| **Day / Time** | Day 7 (Thu 12 Nov) · ~20 min |
| **Prerequisites** | [Step 1.04](04-first-push.md) |
| **Produces** | `CONTRIBUTING.md` at the repository root |

---

## Why bother for a solo project

Two reasons, and neither is bureaucracy:

1. **It is graded.** "Demonstrates a disciplined development process" is a standard
   rubric line. A conventions file plus a history that follows it is direct evidence.
2. **It removes decisions.** Twenty-seven days from now, at 11pm, "what should this
   commit message say" should not be a question you have to answer from scratch.

---

## Do this

Create `CONTRIBUTING.md` at the repository root:

```markdown
# Contributing

Solo capstone project for CCS670. These are the conventions I follow, recorded so
the development process is visible in the repository history.

## Branches

Trunk-based. `main` is always working — it must build and its tests must pass.

| Branch | Use |
|---|---|
| `main` | Always green. Every commit here is a working state |
| `feat/<scope>` | A feature too large for one sitting |
| `fix/<scope>` | A bug fix |
| `docs/<scope>` | Documentation only |

For a solo build, commit directly to `main` for small work. Use a branch when a
change will take more than a day or will break the build while in progress.

## Commit messages

    <type>(<scope>): <what changed>

**Types**

| Type | For |
|---|---|
| `feat` | A new capability |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `test` | Tests only |
| `refactor` | Restructuring with no behaviour change |
| `chore` | Build, dependencies, tooling |
| `style` | Formatting only |

**Scopes**

`repo` `stack` `db` `models` `rides` `pricing` `matching` `payments` `tracking`
`sos` `auth` `ui` `api` `docs`

**Examples**

    feat(rides): add Isang Biyahe trip chain endpoint
    fix(pricing): apply surge multiplier before Pakyawan split
    docs(stack): complete sections 3-5 and fill channel layer rows
    test(matching): cover the no-driver-available timeout
    chore(repo): add gitignore and folder structure

**The rule:** the subject line says *what changed*, in the imperative. If you
cannot write it without the word "and", the commit is doing two things — split it.

## Tags

| Tag | When |
|---|---|
| `v0.1.0` | End of Phase 2 — database complete |
| `v0.2.0` | End of Phase 3 — all 7 features via API |
| `v0.3.0` | End of Phase 4 — UI complete |
| `v1.0.0` | Submitted build (Day 31) |

    git tag -a v0.1.0 -m "Database and domain model complete"
    git push origin v0.1.0

## Daily routine

1. Read today's step in `steps/` in full
2. Build it
3. Run the step's verification
4. Log it in `steps/PROGRESS.md`
5. Commit
6. Push

## Never

- Commit `.env` or any credential
- Commit `node_modules/`, `.venv/`, or `__pycache__/`
- Force-push `main`
- Leave `main` broken overnight
- Make a commit whose message is "update", "fix", or "wip"

## Design changes

The design is frozen (see `docs/plan/design-freeze.md`). To change it:

1. Change the design artefact first — never the code
2. Append an entry to `database/consistency_report.md`
3. Re-render affected diagrams with `-DPLANTUML_LIMIT_SIZE=16384`
4. Record it in the decision log in `steps/PROGRESS.md`
5. Then change the code

The code follows the design, never the reverse.
```

---

## Verify

```powershell
Test-Path CONTRIBUTING.md
git add CONTRIBUTING.md
git commit -m "docs: add contribution and workflow conventions"
git push
```

- [ ] `CONTRIBUTING.md` exists at the root
- [ ] The commit types and scopes match those in `steps/README.md`
- [ ] The design-change procedure matches `docs/plan/design-freeze.md`
- [ ] Pushed

---

## Log it

```markdown
**Step 1.05 — workflow conventions — DONE**

- Wrote CONTRIBUTING.md: branching, commit types/scopes, tags, daily routine,
  design-change procedure
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| Feels like overkill for one person | It is, slightly | It takes 20 minutes once and it is graded. Write it |
| Want to add a PR requirement | Solo project | Skip it. PRs to yourself add ceremony without evidence. Branch when useful, merge when done |
| Conventions already drifting | Normal | Re-read this file at the start of each phase, not each day |
