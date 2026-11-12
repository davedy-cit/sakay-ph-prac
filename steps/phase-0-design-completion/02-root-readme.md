# Step 0.02 — Write the Root README

| | |
|---|---|
| **Goal** | A root `README.md` that lets someone who has never seen this project understand what it is, how it is laid out, and how to run it |
| **Day / Time** | Day 5 (Tue 10 Nov) · ~1 hour |
| **Prerequisites** | [Step 0.01](01-complete-technology-stack.md) — the README should reflect the stack decisions you just recorded |
| **Produces** | `README.md` at the project root |

---

## Why this matters more than it looks

This is the file an assessor opens first. Right now the project root contains only
two folders and no entry point — a reader has to guess where to start among 33
files.

It also **documents the folder layout**, which resolves audit finding A-12:
`database/` sits beside `docs/` rather than inside it. That is defensible, but it
needs explaining. Do **not** move `database/` — `consistency_report.md` and
`schema_listing.md` reference `database/...` paths in roughly thirty places, and
moving it would invalidate every one.

---

## Do this

### 1. Create `README.md` at the project root (~40 min)

Write it in this order. Keep it factual — this is a reference document, not a
pitch. The concept paper is where the persuasion lives.

```markdown
# Sakay.ph — Isang App, Lahat ng Sakyan

A multi-mode ride-hailing platform for every Filipino transport mode.

**CCS670 — Object-Oriented Software Development · Capstone Project**
<Your name> · Master in Information Technology · November–December 2026

---

## What this is

<Three or four sentences. What problem, what solution, what is actually built.
Name the six modes: tricycle, habal-habal, jeepney, UV Express, e-trike, car.>

## The seven features

| Feature | What it does |
|---|---|
| **Lahat ng Sakyan** | Multi-mode booking — one engine, six modes |
| **Isang Biyahe** | First-mile–last-mile trip chaining — one booking, one fare, one receipt |
| **Saan ang Jeep?** | Live route tracking for jeepneys and UV Express |
| **Pakyawan** | Share-ride matching with automatic fare splitting |
| **Sertipikadong Manong** | LGU-accredited driver onboarding |
| **SOS Bantay** | In-ride emergency alert to trusted contacts |
| **Bagyo Mode** | Weather-triggered fare multiplier |

## Stack

<A short table: Python/Django/DRF, MySQL 8.4, Redis, Channels, Vue 3, Tailwind,
Leaflet. Link to docs/proposal/technology_stack.md for the full reasoning.>

## Repository layout

<The tree from the audit's §6. Explain that database/ sits at the root
deliberately, and that steps/ is the build manual.>

## Documentation

| Where | What |
|---|---|
| `docs/proposal/` | Concept paper, proposal deck, technology stack |
| `docs/uml/` | Use case, class, sequence, activity diagrams (development + overview) |
| `database/` | EER/ER diagrams, schema listing (26 tables as audited; 27 once D-62 lands), consistency audit |
| `docs/mockups/` | UI mockups — passenger and driver |
| `docs/review/` | Folder audit and technology stack review |
| `docs/plan/` | Roadmap, milestones, timeline |
| `steps/` | Build instructions and progress log |

## Running it

<Fill this in properly in Phase 1. For now:>

> Not yet runnable — implementation begins 11 November 2026.
> Setup instructions land in Phase 1.

## Status

| Milestone | Dates | Status |
|---|---|---|
| M1 — Design frozen & repository live | 6–12 Nov | 🟡 in progress |
| M2 — Database & domain model | 13–19 Nov | ⬜ |
| M3 — All 7 features via API | 20–27 Nov | ⬜ |
| M4 — UI complete & integrated | 28 Nov – 2 Dec | ⬜ |
| M5 — Tested, documented, submitted | 3–6 Dec | ⬜ |

See `docs/plan/02-roadmap.md` for the full timeline.
```

### 2. Fill in the two placeholders that are already answerable (~15 min)

- **Repository layout** — use the tree from
  [../../docs/review/00-folder-audit.md](../../docs/review/00-folder-audit.md) §6.
  Include a one-line note on why `database/` is at the root rather than under
  `docs/`.
- **The opening description** — write it in your own words. Do not paste the
  concept paper's problem statement; an assessor who has read the proposal will
  recognise it, and a README that quotes the proposal looks assembled rather than
  written.

### 3. Leave the "Running it" section honest (~5 min)

The project is not runnable yet. Say so, with the date implementation begins.
A README that claims a setup procedure which does not exist is worse than one that
admits the current state — and you will replace this section in Phase 1 anyway.

---

## Verify

```powershell
# The file exists at the root
Get-ChildItem -Path . -Filter README.md

# It has real content, not a stub
(Get-Content README.md | Measure-Object -Line).Lines
```

Then read it as if you were the instructor opening the repository for the first
time. Can you tell, without opening another file:

- [ ] what the project is
- [ ] what the seven features are
- [ ] what the stack is
- [ ] where the design artefacts live
- [ ] how far along it is

If any answer requires opening another file, add it.

---

## Log it

In [../PROGRESS.md](../PROGRESS.md), under **Session notes → Day 5**:

```markdown
**Step 0.02 — root README — DONE**

- Wrote README.md: description, 7 features, stack summary, repo layout,
  documentation index, milestone status
- Documented why database/ sits at the root (A-12) — not moving it, ~30 path
  references depend on the current location
- "Running it" left as an honest placeholder until Phase 1
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| Tempted to write a long README | Enthusiasm | Keep it under ~100 lines. It is an index, not the report — the report is a Phase 6 deliverable |
| Unsure what to put in "Running it" | Nothing runs yet | Say exactly that. Replace it on Day 7 |
| Want to move `database/` into `docs/` | Tidiness | Don't. Thirty path references would break for a cosmetic gain. Document the layout instead |
