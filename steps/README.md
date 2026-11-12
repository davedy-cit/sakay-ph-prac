# `steps/` — Your Working Instructions

This folder is your build manual. It is not documentation *about* the project — it
is the sequence of things you do, in order, with the exact commands, the expected
result, and the check that proves the step is finished.

**You do the work. These files tell you exactly what the work is.**

---

## How to use this folder

1. Open [PROGRESS.md](PROGRESS.md) and find the first unchecked step.
2. Open that step's file and **read it end to end before typing anything.** Several
   steps have a "before you start" note that saves you from a dead end.
3. Do the work.
4. **Run the verification.** Every step has one. A step is finished when its check
   passes — not when the code is written.
5. Log it in `PROGRESS.md`: status, what actually happened, blockers, commit SHA.
6. Commit and push. One commit per step.

> **If a step doesn't match reality** — a command fails, a file isn't where the step
> says, a version doesn't exist — that is a finding, not a failure. Note it in the
> step file itself and in `PROGRESS.md`, then tell me. The instructions get fixed,
> and the correction becomes part of your process evidence. Do not silently work
> around it; that is how the design and the build drift apart.

---

## Folder layout

```
steps/
├── README.md                  ← this file
├── PROGRESS.md                ← the master tracker + daily log
├── phase-0-design-completion/ ← Days 1–5   finish the design phase
├── phase-1-repository/        ← Days 6–7   git, GitHub, scaffolds
├── phase-2-database/          ← Days 8–14  27 tables as Django models
├── phase-3-backend-api/       ← Days 15–22 all 7 features via API
├── phase-4-frontend/          ← Days 23–27 the four mockup screens
├── phase-5-integration-testing/ ← Day 28   end-to-end + UAT
└── phase-6-documentation-submission/ ← Days 29–31 report, manual, video
```

Phases 0–2 have one file per step. Phases 3–6 have a single overview file each,
because they will be written in full detail **as you approach them** — their exact
contents depend on decisions made in earlier phases, and writing 34 speculative
step files now would guarantee most of them get rewritten. Each overview lists
every step with its goal and verification, so you can see the shape of the work.

---

## Step file format

Every step file follows the same shape, so you always know where to look:

| Section | What it tells you |
|---|---|
| **Goal** | One sentence — what exists when this step is done |
| **Day / Time** | Which day of the 31, and a realistic duration |
| **Prerequisites** | Steps that must be complete first |
| **Do this** | The actual work, with exact commands |
| **Verify** | The command or observation that proves it worked |
| **Log it** | Exactly what to write in `PROGRESS.md` |
| **If it goes wrong** | The failure modes you are most likely to hit |

---

## Conventions

### Status markers

Used in `PROGRESS.md` and in the step files themselves:

| Marker | Meaning |
|---|---|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Done and verified |
| `[!]` | Blocked — see the blocker log |
| `[-]` | Skipped deliberately — say why |

### Commit messages

```
<type>(<scope>): <what changed>
```

Types: `feat` `fix` `docs` `test` `chore` `refactor` `style`
Scopes: `repo` `stack` `db` `models` `rides` `pricing` `matching` `payments`
`tracking` `sos` `auth` `ui` `api` `docs`

Example: `feat(pricing): apply surge multiplier before Pakyawan split`

### Paths in these files

Commands are written for **PowerShell on Windows**, from the project root:

```
C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem
```

Where a step needs a different directory, it says so explicitly. Remember that
PowerShell needs `;` or a new statement rather than `&&` — and that `cd` inside a
compound command is best avoided; use absolute paths.

---

## The daily loop

Ten minutes of discipline that turns a folder of code into a graded process:

1. **Read** today's step in full.
2. **Build** it.
3. **Verify** it — run the check.
4. **Log** it in `PROGRESS.md`.
5. **Commit** it with a conventional message.
6. **Push** it.

---

## Two things to remember

**The schedule has almost no slack.** 7 features × 27 tables × 2 user roles in 27
remaining days, solo, is a real build. If you fall behind, use the **scope ladder**
in [../docs/plan/02-roadmap.md](../docs/plan/02-roadmap.md) §5 — cut early and
deliberately rather than hoping to catch up. Never cut the 27-table schema, the
fare calculator, the ride lifecycle, or the traceability matrix.

**Three hard freezes:** feature freeze Day 22 (27 Nov), UI freeze Day 27 (2 Dec),
documentation freeze Day 29 (4 Dec). They exist because the last week is always
shorter than it looks.
