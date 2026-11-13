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
`sos` `auth` `ui` `api` `docs` `design` `uml` `plan`

`design`, `uml` and `plan` are documentation scopes already in use in the Phase 1
history (`docs(uml): …`, `docs(plan): …`). A scope may be omitted entirely when a
commit spans the whole repository — the root README commit is an example.

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
