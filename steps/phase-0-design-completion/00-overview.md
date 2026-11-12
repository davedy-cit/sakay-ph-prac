# Phase 0 — Design Completion

**Days 1–5 · 6–10 November 2026 · completed 11 November (Day 6)**
**Status: ✅ all three steps done — the design is frozen**

---

## Goal

Close out the design phase so that nothing downstream is built on an unfinished
document. When this phase ends, the design is **frozen** — no further changes to
the schema, the UML, or the stack without a recorded decision.

Days 1–4 already delivered the hard part: the concept, the UML, the 26-table
schema, and a 61-defect audit. What is left is small but not optional — and one
piece of it, Step 01, grows the schema to **27 tables** by deciding A-13.

---

## Why this phase exists

The whole-folder audit ([../../docs/review/00-folder-audit.md](../../docs/review/00-folder-audit.md))
found three high-severity gaps. Two of them are here:

| ID | Finding |
|---|---|
| **A-01** | `technology_stack.md` is **truncated mid-sentence** at the §3 heading. §4 and §5 are referenced from the body but do not exist |
| **A-02** | **Two stack rows are blank** — `Channel layer` and `Cache / channel backend`. Channels cannot run without a channel layer, so this blocks Phase 3 |
| **A-13** | **Pricing rules visible in the mockups have no home in the schema** — booking fee, commission waiver, chain discount. The `mock3` arithmetic does not even close |

A-03 (no repository) is the third, and Phase 1 handles it.

---

## Steps

| | Step | Time | What exists when it's done |
|---|---|---|---|
| ✅ | [01 — Complete the technology stack document](01-complete-technology-stack.md) | ~2 h | `technology_stack.md` has no truncated sections, no blank rows, and no dangling cross-references. The A-13 pricing gap is decided and recorded as D-62 |
| ✅ | [02 — Write the root README](02-root-readme.md) | ~1 h | A root `README.md` that lets a stranger understand the project, its layout, and how to run it |
| ✅ | [03 — Design freeze check](03-design-freeze-check.md) | ~30 min | `docs/plan/design-freeze.md` — the frozen baseline, with every known limitation listed and D-63 recorded |

---

## Order matters

Do them in the order above. Step 01 decides the pricing rules, Step 02 documents
the project including those decisions, and Step 03 declares the freeze. Doing 02
before 01 means writing a README that immediately goes stale.

---

## What "design complete" means

Not "perfect" — **decided**. Every question that the build will need answered is
either answered or explicitly deferred with a reason. Three questions were open:

1. **How is the booking fee stored?** (A-13) → `RIDE_MODE.booking_fee`
2. **Is the chain discount real, or a mockup artefact?** (A-13) → dropped; no rule justifies it
3. **Does the `mock3` total show ₱48 or ₱51?** (A-13) → ₱51.00; the mockup is wrong

Step 01 closed all three, recorded as **D-62**. Nothing else in the design is open.
The three questions that remain are **implementation** questions with decide-by dates,
not design questions — they are listed in
[`../../docs/plan/design-freeze.md`](../../docs/plan/design-freeze.md) under *Open
questions carried forward*.

---

## Exit criteria

- [x] `technology_stack.md` reads end to end with no missing sections
- [x] No blank cells in the stack table
- [x] Every internal cross-reference (`§4`, `§5`) resolves to a real section
- [x] The A-13 pricing decisions are recorded as **D-62** in `database/consistency_report.md` §3.10
- [x] The UUID storage decision is recorded as **D-63** in `database/consistency_report.md` §3.11
- [x] Root `README.md` exists and explains the folder layout
- [x] The design freeze is recorded in `docs/plan/design-freeze.md` and logged in `steps/PROGRESS.md`
- [ ] First commit made — **Phase 1, Day 6.** The freeze's commit column stays empty
      until the first push succeeds

---

## Next

**Phase 1 — Repository** · Days 6–7 · [../phase-1-repository/00-overview.md](../phase-1-repository/00-overview.md)

If you finish Phase 0 with hours to spare on Day 5, **start Phase 1 the same day.**
The roadmap has almost no slack and this is the easiest place to buy some back.
