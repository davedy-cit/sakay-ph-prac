# Sakay.ph — Whole-Folder Audit

**Audited:** 10 November 2026 · Day 5 of the 31-day window (6 Nov – 6 Dec 2026)
**Auditor:** Claude Code, at the request of the project author
**Scope:** every file under `ride-hailingSystem/` — 33 files, 0 lines of application code

---

## 1. Verdict

**The design phase is unusually strong and is close to complete.** The schema is
genuinely well-reasoned — the weak entity, the three associative entities, the
class-table inheritance, the documented denormalizations, and the 61-defect audit
are work well above the usual capstone standard. The UML set is complete and
internally consistent. The mockups are coherent and product-specific.

**But the project has no repository, no README, no code, and its technology-stack
document is truncated mid-sentence.** Three of the four things needed to begin
building are missing. This audit found **16 further items**, of which 3 are
high-severity.

Nothing here invalidates the design. The work is a solid foundation; the gaps are
about *packaging and completeness*, not about the thinking.

---

## 2. Inventory

| Area | Files | State |
|---|---|---|
| `database/` — EER/ER diagrams | 4 `.puml` + 4 `.png` | Complete, audited, renders verified |
| `database/` — written schema | `schema_listing.md` (26 tables) | Complete |
| `database/` — audit | `consistency_report.md` (61 defects) | Complete |
| `docs/uml/` — development set | 4 `.puml` + 4 `.png` | Complete |
| `docs/uml/` — overview set | 4 `.puml` + 4 `.png` | Complete |
| `docs/mockups/` | 4 `.png` | Complete for passenger; thin for driver |
| `docs/proposal/` | `.docx`, `.pptx`, `technology_stack.md` | **Stack doc truncated** |
| Root | — | **Empty — no README, no `.gitignore`, no git** |
| Source code | — | **None yet** |

**Total:** 33 files — 13 `.puml`, 16 `.png`, 2 `.md`, 1 `.docx`, 1 `.pptx`.

---

## 3. Verification I actually performed

I did not take the documents at their word. I checked:

| Check | Method | Result |
|---|---|---|
| Are the 61 claimed fixes really in the files? | Grepped `er_overview.puml` for D-10…D-15 (`mode_code`, `final_fare`, `<<FK, UQ>>`) and `usecase_overview.puml` for D-41/D-42 | ✅ All sampled fixes present |
| Are any diagrams silently clipped (defect D-61)? | Read every PNG's pixel dimensions | ✅ None clipped. Tallest are `activity_development` 2180×5501 and `sequence_development` 2066×4525 — both **above** PlantUML's 4096 default, which proves the raised limit was used |
| Does the schema listing cover all 26 tables? | Read in full; counted sections 1–26 | ✅ Consecutive, no gaps |
| Is every class mapped to a table? | Cross-read `class_development.puml` against `schema_listing.md` | ✅ 20 classes → 18 tables + 2 services; 4 tables documented as *(added)* |
| Do the mockups agree with the schema? | Read all 4 mockups against the 26 tables | ❌ **Disagreements found — see A-13** |
| Is there any code or repo? | Full recursive listing | ❌ None |

**The consistency report holds up.** I found no case where it claimed a fix that
was not actually applied.

---

## 4. Gaps register

Severity: **H** = blocks the next phase · **M** = will cost marks or time ·
**L** = cosmetic.

### 4.1 High

| ID | Finding | Fix |
|---|---|---|
| **A-01** | **`technology_stack.md` is truncated.** The file ends mid-sentence at the heading `## 3. Verify what is currently installed the system` (line 63). §4 and §5 are **referenced from the body** — line 44 says *"Install as `PyMySQL[rsa]` (see §4)"* and line 34 says *"See §5"* — but **neither section exists**. The document cannot be followed as written. | Complete §3, §4, §5. Step file: [steps/phase-0/01](../../steps/phase-0-design-completion/01-complete-technology-stack.md) |
| **A-02** | **Two stack rows are blank** — `Channel layer` and `Cache / channel backend` (lines 47–48). These are not optional: Django Channels will not run a cross-process channel layer without a backend, and live tracking + SOS both depend on it. | Fill both. Recommendation in [01-technology-stack-review.md](01-technology-stack-review.md) §3 |
| **A-03** | **No repository, no README, no `.gitignore`.** The `Is a git repository: false` flag confirms nothing is under version control. A 31-day build with no commit history is also a grading liability — assessors often weight process evidence. | Phase 1 — see [steps/phase-1-repository/](../../steps/phase-1-repository/) |

### 4.2 Medium

| ID | Finding | Fix |
|---|---|---|
| **A-04** | **No SQL DDL exists.** `schema_listing.md` §*Design decisions* item 5 states this was deliberate. Django migrations will generate the DDL, but until code exists there is no artifact a grader can run, and no way to prove the implementation matches the 26-table design. | **Resolved.** `docs/schema.sql` is exported after the first migration ([steps/phase-2-database/08](../../steps/phase-2-database/08-migrations-seed-and-admin.md)), and the schema-contract test asserts the 27 tables, the four composite keys and the enum widths executably ([steps/phase-2-database/09](../../steps/phase-2-database/09-model-tests.md)) |
| **A-05** | **Stack is missing whole categories** — ASGI server, test frameworks (backend *and* frontend), linters/formatters, CI, Docker, geospatial library, seed data, and a driver simulator. Full analysis in the stack review. | [01-technology-stack-review.md](01-technology-stack-review.md) §4 |
| **A-06** | **No traceability matrix.** Nothing links *requirement → use case → class → table → API endpoint → screen → test*. For a capstone this is the single highest-value missing document: it is the artifact that proves the OO design was actually carried through to working software, which is precisely what CCS670 grades. | Build it in Phase 5, populate it as you go — see [steps/PROGRESS.md](../../steps/PROGRESS.md) |
| **A-07** | **Mockups cover 4 passenger screens and only 1 driver screen**, but the use-case diagram defines **27 use cases** across 5 actors. The driver flow (online/offline toggle, accepting, start/end trip, earnings, payout, accreditation renewal) has no screen design beyond a single request card. | Accept for now — the passenger screens are the graded UI. Design driver screens on the fly in Phase 4 and update the mockups |
| **A-08** | **No non-functional requirements.** Nothing states performance, security, availability or usability targets. The final report will need them, and without them "fully functional" is undefined. | Add an NFR section to the final report; a starter set is in the roadmap |
| **A-09** | **Filipino/English interface is promised** (concept paper §5, both personas) **but no i18n library is in the stack.** | Either add `vue-i18n` or scope to English and document the deviation. Recommendation: English UI with Filipino feature names (already the case in the mockups) and document it |
| **A-10** | **No diagram render script.** Defect D-61 proved that a failed or clipped PlantUML render still writes a PNG **and exits 0** — the trap that silently truncated two diagrams. With 13 `.puml` files, re-rendering by hand will re-introduce it. | Add `tools/render-diagrams.ps1` pinning `-DPLANTUML_LIMIT_SIZE=16384` and asserting exit code 0 |
| **A-11** | **No seed-data strategy.** `RIDE_MODE`, `PAYMENT_METHOD` and `LGU_UNIT` are lookup tables the whole app reads. With no seed fixture, the first `runserver` gives an empty booking screen. | Seed fixtures in Phase 2 — [steps/phase-2-database/08](../../steps/phase-2-database/08-migrations-seed-and-admin.md) |

### 4.3 Low

| ID | Finding | Fix |
|---|---|---|
| **A-12** | `database/` sits beside `docs/` at the top level rather than inside it. Defensible (the schema is a first-class artifact), but inconsistent. **Do not move it** — `consistency_report.md` and `schema_listing.md` both reference `database/...` paths in ~30 places, and moving would invalidate every one. | Document the layout in the root README instead |
| **A-13** | **Pricing rules visible in the mockups have no home in the schema.** See §5 — this is the one substantive design gap I found. | **Resolved 11 Nov.** Decided and recorded as **D-62** in `database/consistency_report.md`. `RIDE_MODE.booking_fee` and `PLATFORM_CONFIG` (table 27) land in Phase 2, Steps 02.01 and 02.03; the chain discount was dropped and the `mock3` total corrected to ₱51.00 |
| **A-14** | Mockups are PNG-only with no editable source. | Accept — Phase 4 builds the real screens; treat the PNGs as the visual spec |
| **A-15** | No root README or docs index, so a reader cannot navigate 33 files. | Phase 0 — [steps/phase-0-design-completion/02](../../steps/phase-0-design-completion/02-root-readme.md) |
| **A-16** | No risk register, no decision log. The consistency report is an excellent *retrospective* audit but there is no forward-looking log. | [steps/PROGRESS.md](../../steps/PROGRESS.md) carries both |

---

## 5. A-13 in detail — the one substantive design gap

I read the four mockups against the 26-table schema. Four pricing behaviours are
**shown to the user in the UI but cannot be stored or computed** by the current
design:

| Mockup | Shows | Schema support |
|---|---|---|
| `mock3_payment.png` | `Booking fee ₱3.00` | ❌ No column anywhere. `RIDE_MODE` has `base_fare` and `per_km_rate` only |
| `mock4_driver.png` | `Full fare — no commission on first 5 trips` | ❌ No commission rate and no per-driver trip counter used as a promotion. `DRIVER.total_trips` exists but nothing reads it as a promo trigger |
| `mock1_home.png` | Chain legs priced **below** standalone: tricycle ₱22 in-chain vs ₱25 standalone; e-trike ₱17 in-chain vs ₱30 standalone | ❌ No rule explains the chain discount. `RIDE_LEG.fare` stores the result but nothing computes it |
| `mock3_payment.png` | `₱144.00 − ₱96.00 + ₱3.00 = ₱48.00` | ❌ **Arithmetic does not close.** 144 − 96 = 48, then +3 should be **₱51.00**, but the total reads ₱48.00 |

**Why this matters.** `FareCalculator.computeFare(leg, pax)` and
`applyPakyawanSplit(fare, pax)` are the only pricing operations in the class
diagram. They cannot produce any of the four behaviours above. When you reach
Phase 3 you will either invent these rules mid-build — which is how schemas drift
— or ship a UI that promises prices the backend cannot reproduce.

**Recommended resolution** (cheapest path that keeps the mockups honest):

1. **Booking fee** — add `RIDE_MODE.booking_fee DECIMAL(8,2) NOT NULL DEFAULT 0`.
   It is a per-mode flat fee, so it belongs on the mode row, not on `RIDE`.
2. **Commission waiver** — add `DRIVER.commission_waived_until_trip INT NULL`, or
   simpler: keep commission as a `PLATFORM_CONFIG` key-value table and treat the
   first-5-trips waiver as a rule in `FareCalculator`, documented as a business
   rule rather than a schema change.
3. **Chain discount** — either drop it from the mockup (make in-chain legs cost the
   same as standalone) **or** add `RIDE.chain_discount DECIMAL(10,2)` and document
   the rule. Dropping it is the cheaper and more defensible choice.
4. **Fix the mockup arithmetic** — correct the ₱48.00 total to ₱51.00, or move the
   booking fee outside the "You paid" line.

Record whichever you choose in `database/consistency_report.md` as a new entry
(D-62) so the audit trail stays unbroken — the existing report is good precisely
because every change is traceable.

### 5.1 Resolution — decided 11 November 2026

**All four behaviours were resolved as recommended above.** Recorded as **D-62** in
`database/consistency_report.md` §3.10, which is now the authoritative version of this
decision.

| # | Behaviour | Decision |
|---|---|---|
| 1 | Booking fee | `RIDE_MODE.booking_fee DECIMAL(8,2) NOT NULL DEFAULT 0` — added in Phase 2, Step 02.03 |
| 2 | Commission waiver | Commission rate in a new `PLATFORM_CONFIG` key-value table (table 27); the first-5-trips waiver is a rule in `FareCalculator`, not a schema change — Phase 2, Step 02.01 |
| 3 | Chain discount | **Dropped.** In-chain legs cost the same as standalone. No rule anywhere justifies the discount, and inventing one would mean defending the invention |
| 4 | `mock3` arithmetic | **Corrected to ₱51.00.** The PNG was not edited — see D-62 for why |

**Consequence for the table count.** The design now has **27 tables**, not 26.
`schema_listing.md` is updated in Phase 2 before the first migration; until then every
document still saying "26 tables" is describing the pre-D-62 design. This is expected —
D-62 is `decided`, not yet `implemented`.

---

## 6. Recommended folder structure

Extending what exists, without moving anything that is already referenced:

```
ride-hailingSystem/
├── README.md                    ← NEW  (A-15)
├── .gitignore                   ← NEW  (A-03)
├── .env.example                 ← NEW  Phase 1
├── docker-compose.yml           ← NEW  Phase 1  (MySQL + Redis)
├── backend/                     ← NEW  Phase 2  (Django)
├── frontend/                    ← NEW  Phase 4  (Vue 3)
├── tools/
│   └── render-diagrams.ps1      ← NEW  (A-10)
├── database/                    ← keep in place (A-12)
│   ├── diagrams/                4 .puml + 4 .png
│   ├── schema_listing.md
│   ├── consistency_report.md
│   └── schema.sql               ← NEW  Phase 2  (A-04)
├── docs/
│   ├── proposal/                .docx, .pptx, technology_stack.md
│   ├── uml/                     8 .puml + 8 .png
│   ├── mockups/                 4 .png
│   ├── review/                  ← NEW  this file + stack review
│   └── plan/                    ← NEW  roadmap + timeline
└── steps/                       ← NEW  your working instructions
    ├── README.md
    ├── PROGRESS.md
    └── phase-N-*/
```

**One repository, two apps** (`backend/` + `frontend/`), not two repositories.
Rationale in the roadmap — short version: one commit history, one README, one
submission link, and the frontend and backend version together.

---

## 7. What this means for the next 26 days

The design is ~90% done. What remains in Phase 0 is **finishing the stack
document and writing a README** — under a day of work. That means Phase 1
(repository) can start **today, Day 5**, and you are not behind.

The real risk is not the design. It is that **7 features × 27 tables × 2 user
roles in 26 remaining days, solo, is a large build.** The roadmap addresses this
with a hard feature freeze and a scope ladder — see
[../plan/02-roadmap.md](../plan/02-roadmap.md) §5.
