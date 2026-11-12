# Step 0.03 — Design Freeze Check

| | |
|---|---|
| **Goal** | The design is formally frozen, with every known limitation and open question listed in one place |
| **Day / Time** | Day 5 (Tue 10 Nov) · ~30 minutes |
| **Prerequisites** | [Step 0.01](01-complete-technology-stack.md), [Step 0.02](02-root-readme.md) |
| **Produces** | `docs/plan/design-freeze.md` — the frozen baseline |

---

## Why freeze anything

Because the alternative is discovering on Day 20 that the schema changed on Day 12
and three features were built against the old one. A freeze is not a promise never
to change the design — it is a promise that **any change is recorded**, so the
documents and the code cannot silently diverge.

Your `consistency_report.md` already demonstrates this discipline: it found 61
defects and traced every fix. The freeze extends that same practice forward in
time.

---

## Do this

### 1. Record the UUID storage decision first (~10 min)

This step produces a design change — **D-63** — so it follows the same procedure as every
other one: **the artefact first, the register second, the document third.**

**1a. The artefact.** `schema_listing.md` types every primary and foreign key as `UUID`.
MySQL 8.4 has **no native `UUID` column type**, so Django's `UUIDField` stores those
values as `CHAR(32)` — the 32-character hex form, no dashes. Add a short "About the `UUID`
type" note to the listing's preamble, so that a reader who runs `SHOW CREATE TABLE` finds
an explanation rather than a surprise.

**1b. The register.** Append **D-63** to `database/consistency_report.md` as **§3.11**,
in the same format as §3.10. This is a *decision*, not a defect the audit found — say so
in the entry, exactly as D-62 does, so the "D-01 … D-61 are all fixed" statement stays
true.

**No diagram re-render is needed.** The EER diagrams show entities, keys and
cardinalities; none of them displays a storage type, so nothing in `database/diagrams/`
changes.

**Why not store `BINARY(16)`?** It halves the storage and indexes faster. Rejected: it
needs a custom field and a hand-written migration, and it breaks `UUIDField`'s admin and
form handling — real complexity for a saving nothing in this project can measure.

### 2. Create `docs/plan/design-freeze.md` (~25 min)

```markdown
# Sakay.ph — Design Freeze

**Frozen:** 11 November 2026
**Baseline:** the design artefacts listed below, as they stand at this commit.
**Milestone:** M1 — *Design frozen & repository live* (6–12 Nov)

## What is frozen

| Artefact | Version | Frozen at commit |
|---|---|---|
| `docs/proposal/Sakay.ph_Project_Concept.docx` | Part 1 — project concept | |
| `docs/proposal/Sakay.ph_Proposal.pptx` | Proposal deck | |
| `docs/proposal/technology_stack.md` | complete (Step 0.01) — §1–§7 | |
| `docs/uml/use-case/usecase_development.puml` | 27 use cases, 5 actors | |
| `docs/uml/class/class_development.puml` | 20 classes, 8 enums | |
| `docs/uml/sequence/sequence_development.puml` | interaction per feature | |
| `docs/uml/activity/activity_development.puml` | swimlane process flow | |
| `docs/uml/*/*_overview.puml` | 4 simplified overview diagrams | |
| `database/diagrams/eer_development.puml` | 26 tables as drawn — **table 27 (`PLATFORM_CONFIG`, D-62) is added to the diagram in Phase 2, Step 02.01** | |
| `database/diagrams/eer_core.puml`, `eer_features.puml` | the same EER in two parts | |
| `database/diagrams/er_overview.puml` | simplified crow's-foot ER | |
| `database/schema_listing.md` | 26 tables, 13 domains as written — **gains table 27 and `RIDE_MODE.booking_fee` in Phase 2, before the first migration** | |
| `database/consistency_report.md` | 61 defects + D-62 + D-63 | |
| `docs/mockups/mock1_home.png` … `mock4_driver.png` | 4 screens | |

**Leave the commit column empty.** It is filled on Day 6, immediately after the first
push in Phase 1. Add a line under the table saying so — otherwise an empty column reads
as an oversight rather than a plan, and an empty commit column after Day 7 means the
freeze is unfinished. A baseline you cannot point at a commit for is not a baseline.

## What a freeze does and does not cover

**Covered.** The schema, the UML model, the technology choices, the mockups, and the
feature list. These change only through the procedure below.

**Not covered.** Implementation detail — class and method names, serializer shapes, the
order of query clauses, which of two equivalent Django idioms you pick. Those belong in
the code, where they can change freely. If you find yourself wanting to change *the
design*, use the procedure. If you are choosing between two ways to *write* it, just
write it.

## How to change the design after this point

1. Make the change in the design artefact first, not the code.
2. Append an entry to `database/consistency_report.md` — **the next free number is D-64**
   (D-62 is A-13, D-63 is the UUID decision recorded in this step). Read the last entry in
   the file to confirm before you write it.
3. Re-render every affected diagram — with `-DPLANTUML_LIMIT_SIZE=16384`.
4. Record the change in `steps/PROGRESS.md` decision log.
5. Only then change the code.

**The rule:** the code follows the design, never the reverse. When you find the
design is wrong — and you will — fix the design first. That single habit is most of
what separates a project that scores well from one that does not.

## Known limitations

<Copy the 8 items from database/consistency_report.md §4, plus:>

9. **Pricing rules (D-62).** Booking fee, commission waiver and chain discount —
   see D-62 for how each was resolved. Note that `mock3_payment.png` still shows
   ₱48.00; the PNG is the design input and was deliberately not edited.
10. **UUID storage (D-63).** MySQL has no native `UUID` type, so Django's
    `UUIDField` stores every key as `CHAR(32)` rather than `BINARY(16)`. Same value,
    twice the bytes, no measurable cost here. Recorded so that `SHOW CREATE TABLE`
    matching the design is explained rather than surprising.
11. **OTP is simulated.** No SMS gateway. The code is returned in the API response
    and logged when `DEBUG=True`.
12. **Payment, delivery and position are all simulated providers.** No real money,
    no real gateway, no GPS hardware.
13. **One Vue application with role-based routes**, not separate passenger and
    driver apps.

**Do not add `TRIP_TRACKING` pings to this list.** §4 already carries it as item 4 —
a position cannot be attributed to a specific leg of an Isang Biyahe chain. Listing it
twice makes a 13-item list look like 14 and invites the reader to hunt for the
difference.

## Open questions carried forward

| # | Question | Decide by |
|---|---|---|
| Q1 | Does the driver flow need more screens than `mock4` provides? | Day 23 (Phase 4) |
| Q2 | Is the `Saan ang Jeep?` map fed by WebSocket or polling as a fallback? | Day 21 (Phase 3) |
| Q3 | What are the final NFR targets? | Day 28 (Phase 5) |

## Sign-off

- [ ] Every artefact in the table above exists on disk
- [ ] `database/consistency_report.md` contains **D-62** (§3.10) and **D-63** (§3.11)
- [ ] The decision log in `steps/PROGRESS.md` is current
- [ ] No open question lacks a "decide by" date
- [ ] `README.md` exists at the project root and reflects this freeze
- [ ] The commit column above is filled in — **Day 6, after the first push**
```

### 3. Fill in the commit column honestly (~5 min)

The commit SHAs go in **after** the first push in Phase 1. Leave them blank now,
fill them on Day 6, and treat an empty commit column on Day 7 as an unfinished
freeze.

### 4. Re-render the diagrams once, as a baseline (~5 min)

If you have PlantUML available, re-render all 13 diagrams now and confirm exit
code 0 for each. This proves the frozen artefacts are reproducible from source —
which is the whole point of committing `.puml` alongside `.png`.

```powershell
# From the project root — adjust the plantuml.jar path to yours
java -DPLANTUML_LIMIT_SIZE=16384 -jar plantuml.jar -tpng "database\diagrams\*.puml"
java -DPLANTUML_LIMIT_SIZE=16384 -jar plantuml.jar -tpng "docs\uml\**\*.puml"
```

> **`-DPLANTUML_LIMIT_SIZE=16384` is not optional.** Defect D-61: a diagram taller
> than PlantUML's 4096 px default is **silently clipped, and the process still
> exits 0**. Two of your diagrams were truncated this way and looked like
> successful renders. Check the exit code, and check the pixel height of the
> output.

If PlantUML is not set up yet, skip this — it is Phase 1 Step 06 work. Note it as
deferred rather than pretending it ran.

---

## Verify

```powershell
Test-Path "docs\plan\design-freeze.md"
Get-Content "docs\plan\design-freeze.md" | Select-String -Pattern '^## '
```

- [ ] `docs/plan/design-freeze.md` exists
- [ ] Every artefact in the table exists on disk
- [ ] `consistency_report.md` contains a **D-62** entry (§3.10) **and a D-63 entry** (§3.11)
- [ ] `schema_listing.md` carries the "About the `UUID` type" note (D-63)
- [ ] Every open question has a "decide by" date
- [ ] The decision log in `PROGRESS.md` reflects today's decisions (D-08 … D-17)
- [ ] `README.md` exists at the project root — Step 0.02, which this step depends on

---

## Log it

In [../PROGRESS.md](../PROGRESS.md):

```markdown
**Step 0.03 — design freeze — DONE**

- Recorded D-63 (UUID storage on MySQL) — schema_listing.md note first, then the
  §3.11 register entry. No diagram re-render needed
- Wrote docs/plan/design-freeze.md: 14 frozen artefacts, the change procedure,
  13 known limitations, 3 open questions with decide-by dates, sign-off checklist
- Commit column left empty on purpose — filled after the first push on Day 6
- Re-rendered all 13 diagrams with -DPLANTUML_LIMIT_SIZE=16384 — all exit 0
  (or: deferred to Phase 1 Step 06 if PlantUML is not installed)
- **Phase 0 complete.** Design frozen at <sha>
- **Commit:** <sha>
```

Then tick the Phase 0 boxes in the master tracker and update the milestone status
in the root README.

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| The freeze feels premature — you want to keep designing | Normal | The design is genuinely done. Remaining uncertainty is *implementation* detail, which belongs in the code, not the design |
| You spot a real design flaw while writing this | Good — that is the exercise | Fix the artefact, add a `consistency_report.md` entry, then freeze. Better now than on Day 20 |
| PlantUML will not run | Not installed | Defer to Phase 1 Step 06. Note it as deferred; do not mark it done |
| A diagram renders but looks truncated | D-61 again | You forgot `-DPLANTUML_LIMIT_SIZE=16384`, or you are reading the old PNG. Check the pixel height against the pre-freeze dimensions recorded in the audit |

---

## Phase 0 complete

When all three steps are done, the design phase is closed. Move to
[../phase-1-repository/00-overview.md](../phase-1-repository/00-overview.md).

If Day 5 still has hours left in it, **start Phase 1 today.**
