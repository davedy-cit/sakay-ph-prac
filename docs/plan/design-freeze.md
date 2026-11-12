# Sakay.ph — Design Freeze

**Frozen:** 11 November 2026
**Baseline:** the design artefacts listed below, as they stand at this commit.
**Milestone:** M1 — *Design frozen & repository live* (6–12 Nov)

> **Why this date and not 10 November.** Steps 0.02 and 0.03 are Day 5 work, but Days
> 1–4 ran 6–9 November and the stack document was finished on 11 November. The design
> has not changed since Day 4 — only the documents describing it have. See
> `steps/PROGRESS.md` for the day-by-day record.

---

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
| `database/diagrams/eer_development.puml` | 26 tables as drawn — **table 27 lands in Phase 2** | |
| `database/diagrams/eer_core.puml`, `eer_features.puml` | the same EER in two parts | |
| `database/diagrams/er_overview.puml` | simplified crow's-foot ER | |
| `database/schema_listing.md` | 26 tables, 13 domains — **gains table 27 in Phase 2** | |
| `database/consistency_report.md` | 61 defects fixed + D-62 + D-63 | |
| `docs/mockups/mock1_home.png` … `mock4_driver.png` | 4 screens | |

**The commit column is intentionally empty.** It is filled on **Day 6**, immediately
after the first push in Phase 1. An empty commit column after Day 7 means the freeze is
not finished — a baseline you cannot point at a commit for is not a baseline.

---

## What a freeze does and does not cover

**Covered.** The schema, the UML model, the technology choices, the mockups, and the
feature list. These change only through the procedure below.

**Not covered.** Implementation detail — class and method names, serializer shapes, the
order of query clauses, which of two equivalent Django idioms you pick. Those belong in
the code, where they can change freely. If you find yourself wanting to change *the
design*, use the procedure. If you are choosing between two ways to *write* it, just
write it.

---

## How to change the design after this point

1. Make the change in the **design artefact** first — `schema_listing.md`, a `.puml`
   file, the mockups. Never start from the code.
2. Append an entry to `database/consistency_report.md`. **The next free number is
   D-64** — read the last entry in the file to confirm before you write it.
3. Re-render every affected diagram with
   `java -DPLANTUML_LIMIT_SIZE=16384 -jar plantuml.jar` (defect D-61: without the limit,
   an over-tall diagram is clipped **silently and still exits 0**).
4. Record the decision in the decision log in `steps/PROGRESS.md`.
5. **Only then** change the code.

**The rule:** the code follows the design, never the reverse. When you find the design is
wrong — and you will — fix the design first. That single habit is most of what separates
a project that scores well from one that does not.

---

## Known limitations

Not defects. Decisions, recorded so they are not mistaken for oversights. Items 1–8 are
copied from `database/consistency_report.md` §4; items 9–13 were added at the freeze.

1. **`MatchingEngine.searchRadiusKm` is not persisted.** It is runtime configuration, not
   platform state; the schema has no column for it.
2. **`DRIVER_PAYOUT` is driver-scoped, not ride-scoped.** A payout settles a balance
   spanning many rides, so there is no single `ride_id` to point at. Per-ride earnings
   remain derivable through `RIDE.driver_id` → `RIDE_LEG.fare`.
3. **`RIDE.fare_estimate` does not record which surge produced it.** The estimate is a
   quote; the multiplier *actually applied* is recorded per leg in `RIDE_LEG.surge_id`,
   which is the auditable figure.
4. **`TRIP_TRACKING` pings belong to the ride, not the leg.** A ping has no `leg_no`, so a
   position cannot be attributed to a specific leg of an Isang Biyahe chain. Acceptable
   for the *Saan ang Jeep?* map; a per-leg trail would need the extra key.
5. **`SOS_ALERT.raised_by` points at USER, while the class diagram has
   `Passenger.triggerSOS()`.** The FK is deliberately wider — a driver or an admin may
   also raise an alert.
6. **No SQL DDL was generated.** The listing is the written schema reference, per the
   original decision. `docs/schema.sql` is exported in Phase 2, once migrations exist to
   export.
7. **`er_overview.puml` is a deliberate simplification** of the EER — no subtypes, no
   feature tables. Its note says so; it is not meant to be a second EER.
8. **`CancelResult` is a return value, not an entity.** It is persisted as CANCELLATION,
   but `Ride.cancel()` and `Driver.cancelTrip()` both return it, so it appears in the
   class diagram as a value object rather than a table.
9. **Pricing rules (D-62).** The booking fee, the commission waiver and the chain-leg
   discount shown in the mockups had no schema home. Resolved by adding
   `RIDE_MODE.booking_fee` and a `PLATFORM_CONFIG` table, dropping the chain discount,
   and correcting `mock3`'s total to ₱51.00. See D-62 for the reasoning. **`mock3_payment.png`
   still shows ₱48.00** — the PNG is the design input and was deliberately not edited.
10. **UUID storage (D-63).** MySQL has no native `UUID` type, so Django's `UUIDField`
    stores every key as `CHAR(32)` rather than the `BINARY(16)` a hand-written field would
    use. Same value, twice the bytes, no measurable cost here. Recorded so
    `SHOW CREATE TABLE` matching the design is explained rather than surprising.
11. **OTP is simulated.** No SMS gateway is integrated. The code is returned in the API
    response and logged when `DEBUG=True`.
12. **Payment, delivery and position are all simulated providers.** No real money moves,
    no real gateway is called, and no GPS hardware is read. The gateway adapter, the SOS
    fan-out and the driver simulator are real code with a simulated transport underneath.
13. **One Vue application with role-based routes**, not separate passenger and driver
    apps. Fewer moving parts, one build, one deployment — and the mockups are a single app
    anyway.

---

## Open questions carried forward

| # | Question | Decide by |
|---|---|---|
| Q1 | Does the driver flow need more screens than `mock4_driver.png` provides? | Day 23 (Phase 4) |
| Q2 | Is the *Saan ang Jeep?* map fed by WebSocket, or does it need a polling fallback? | Day 21 (Phase 3) |
| Q3 | What are the final non-functional targets — response time, concurrent users, uptime? | Day 28 (Phase 5) |

Each has a date because an open question without one is a question that stays open.

---

## Sign-off

- [ ] Every artefact in the table above exists on disk
- [ ] `database/consistency_report.md` contains **D-62** (§3.10) and **D-63** (§3.11)
- [ ] The decision log in `steps/PROGRESS.md` is current
- [ ] No open question lacks a "decide by" date
- [ ] `README.md` exists at the project root and reflects this freeze
- [ ] The commit column above is filled in — **Day 6, after the first push**

---

## After the freeze

Phase 0 is closed. Next: **[Phase 1 — Repository](../../steps/phase-1-repository/00-overview.md)** —
git, GitHub, the Docker stack, and the two application scaffolds. The design does not
change again without a D-number.
