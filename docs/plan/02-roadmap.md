# Sakay.ph — Roadmap, Timeline and Daily Deliverables

**Window:** 6 November 2026 → 6 December 2026 · **31 days**
**Today:** 10 November 2026 · **Day 5 of 31**
**Scope:** all 7 features (5 core + SOS Bantay + Bagyo Mode, the latter two simplified)
**Real-time:** Django Channels + Redis via Docker
**Solo build.** Every day below assumes one person working roughly 6–8 hours.

---

## 1. Where you are

Four of the thirty-one days are spent, and they bought you a complete design phase:

| Day | Date | Delivered |
|---|---|---|
| 1 | Fri 6 Nov | Concept paper (`.docx`) + proposal deck (13 slides) |
| 2 | Sat 7 Nov | Use case, class, sequence, activity diagrams — development + overview |
| 3 | Sun 8 Nov | EER/ER diagrams — 4 diagrams, 26 tables |
| 4 | Mon 9 Nov | `schema_listing.md` (26 tables) + `consistency_report.md` (61 defects fixed) |
| **5** | **Tue 10 Nov** | **← you are here** |

**You are not behind.** The design work is genuinely strong and it is the part most
capstones get wrong. The remaining 27 days are for building.

---

## 2. Milestones

Five milestones. Each has an **exit criterion** — a single observable thing that is
either true or not. Do not start the next milestone until the current one's exit
criterion passes. That discipline is what keeps a 27-day build from drifting.

| # | Milestone | Days | Dates | Exit criterion |
|---|---|---|---|---|
| **M1** | **Design frozen & repository live** | 1–7 | 6–12 Nov | `git push` succeeds; a stranger can clone the repo, read the README, and understand the project without asking you anything |
| **M2** | **Database & domain model implemented** | 8–14 | 13–19 Nov | `python manage.py migrate` runs clean on an **empty volume**; `python manage.py seed_lookups` is idempotent; the schema-contract test proves all **27** tables and the four composite keys exist; `docs/schema.sql` is exported for the reader |
| **M3** | **All 7 features working via API** | 15–22 | 20–27 Nov | Swagger UI at `/api/docs/` can drive a complete ride — book → match → chain → Pakyawan split → track → SOS → surge → pay → receipt → payout → rate — with no frontend involved |
| **M4** | **UI complete & integrated** | 23–27 | 28 Nov – 2 Dec | All four mockup screens are live in the browser, driven by real API calls, and the vehicle moves on the map |
| **M5** | **Tested, documented, submitted** | 28–31 | 3–6 Dec | Test suite green, traceability matrix complete, report + manual + video + deck delivered |

### Milestone map

```
Day  1  2  3  4  5  6  7 │ 8  9 10 11 12 13 14 │15 16 17 18 19 20 21 22 │23 24 25 26 27 │28 29 30 31
     ├──────────────────┼─────────────────────┼────────────────────────┼──────────────┼──────────
M1   ████████████████████
M2                       ██████████████████████
M3                                             ████████████████████████
M4                                                                     ██████████████
M5                                                                                    ██████████
     └ design ┘└ repo ┘  └──── models ────┘    └────── features ──────┘  └─── UI ───┘  └─ ship ─┘
                                                                              ▲
                                                                        FEATURE FREEZE
```

---

## 3. Daily deliverables

Every day ends with **one commit** containing **one concrete artifact**. "Worked on
X" is not a deliverable; "X exists and does Y" is. Days already spent are shown for
the record.

### M1 — Design frozen & repository live · Days 1–7 · 6–12 Nov

| Day | Date | Deliverable | Step file |
|---|---|---|---|
| 1 | Fri 6 Nov | ✅ Concept paper + proposal deck | — done |
| 2 | Sat 7 Nov | ✅ 4 UML diagrams (development) + 4 overviews | — done |
| 3 | Sun 8 Nov | ✅ 4 EER/ER diagrams, 26 tables | — done |
| 4 | Mon 9 Nov | ✅ `schema_listing.md` + `consistency_report.md` | — done |
| 5 | Tue 10 Nov | ✅ `technology_stack.md` complete — §1–§7 written, both blanks filled, 13 rows added, no blank cells. A-13 decided and recorded as **D-62**. *(Worked 11 Nov.)* | [phase-0/01](../../steps/phase-0-design-completion/01-complete-technology-stack.md) |
| **5b** | **Tue 10 Nov** | ⬜ **NEXT UP.** Root `README.md` written ([Step 0.02](../../steps/phase-0-design-completion/02-root-readme.md)), then the design-freeze check ([Step 0.03](../../steps/phase-0-design-completion/03-design-freeze-check.md)). | [phase-0](../../steps/phase-0-design-completion/) |
| 6 | Wed 11 Nov | Git repo initialised, `.gitignore` + folder structure in place, GitHub remote created, first push. | [phase-1](../../steps/phase-1-repository/) |
| 7 | Thu 12 Nov | `docker compose up` brings up MySQL + Redis; Django + Vue scaffolds created; `requirements.txt` and `package.json` install clean; `.env.example` committed. | [phase-1](../../steps/phase-1-repository/) |

> **⚠ You are one day behind — and the gap is now narrow.** Today is **Day 6
> (Wed 11 Nov)**. Step 0.01 is done, so the remaining Day 5 work is the root `README.md`
> and the design-freeze check — **under an hour combined**. Do both, then Day 6's
> repository work, and you are back on schedule.
>
> What is still true: there is no root `README.md`, no git repository, and no Docker
> Desktop. Days 8–14 (M2, the 27 models) are the largest block in the plan and have no
> slack behind them, so the gap has to close today.

### M2 — Database & domain model · Days 8–14 · 13–19 Nov

| Day | Date | Deliverable | Step file |
|---|---|---|---|
| 8 | Fri 13 Nov | Five apps created (`core`, `accounts`, `rides`, `payments`, `safety`); **all 13 domains as `TextChoices`**; shared abstract models and conventions fixed; **`PLATFORM_CONFIG` added as table 27 (D-62)** | [phase-2/01](../../steps/phase-2-database/01-apps-and-shared-conventions.md) |
| 9 | Sat 14 Nov | `settings.py` reads `.env`; **Django connects to MySQL in Docker**; utf8mb4 round-trip and Redis verified on both paths | [phase-2/02](../../steps/phase-2-database/02-settings-env-and-docker.md) |
| 10 | Sun 15 Nov | **Models: `RIDE_MODE`, `USER`, `PASSENGER`, `DRIVER`, `VEHICLE`, `LGU_UNIT`, `ACCREDITATION`** — class-table inheritance, `AUTH_USER_MODEL` set, phone login working | [phase-2/03](../../steps/phase-2-database/03-models-accounts.md) |
| 11 | Mon 16 Nov | **Models: `LOCATION`, `RIDE`, `RIDE_LEG`** — the weak entity's composite key `(ride_id, leg_no)` enforced and verified | [phase-2/04](../../steps/phase-2-database/04-models-rides-core.md) |
| 12 | Tue 17 Nov | **Models: `SURGE_PERIOD`, `PAKYAWAN_GROUP`, `PASSENGER_PREFERRED_MODE`, `TRIP_TRACKING`, `CANCELLATION`, `RATING`** | [phase-2/05](../../steps/phase-2-database/05-models-rides-features.md) |
| 13 | Wed 18 Nov | **Models: `PAYMENT_METHOD`, `WALLET`, `WALLET_TXN`, `PAYMENT`, `FARE_SHARE`, `RECEIPT`, `DRIVER_PAYOUT`; then `SOS_ALERT`, `TRUSTED_CONTACT`, `SOS_NOTIFICATION`** — all 27 tables defined | [phase-2/06](../../steps/phase-2-database/06-models-payments.md), [phase-2/07](../../steps/phase-2-database/07-models-safety.md) |
| 14 | Thu 19 Nov | **`migrate` clean on a fresh volume; `seed_lookups` idempotent; admin shows all 27 models; model + schema-contract tests pass; M2 checkpoint** | [phase-2/08](../../steps/phase-2-database/08-migrations-seed-and-admin.md), [phase-2/09](../../steps/phase-2-database/09-model-tests.md) |

### M3 — All 7 features via API · Days 15–22 · 20–27 Nov

| Day | Date | Deliverable | Step file |
|---|---|---|---|
| 15 | Fri 20 Nov | JWT auth live: register (passenger + driver), login, refresh; **simulated OTP** with Redis TTL | 01 auth-jwt |
| 16 | Sat 21 Nov | Serializers + viewsets for core entities; **`/api/docs/` Swagger UI renders** | 02 serializers |
| 17 | Sun 22 Nov | **`FareCalculator`** — base fare + per-km + booking fee + Pakyawan split + surge multiplier, with unit tests | 03 fare-calculator |
| 18 | Mon 23 Nov | **`MatchingEngine`** — radius search via geopy, driver accept/decline, **timeout path** (the D-43 fix, now real code) | 04 matching-engine |
| 19 | Tue 24 Nov | **Ride lifecycle** end to end + cancellation policy (fee/refund) | 05 ride-lifecycle-api |
| 20 | Wed 25 Nov | **Isang Biyahe** trip chain + **Pakyawan** grouping + `FARE_SHARE` splitting | 06 trip-chain, 07 pakyawan |
| 21 | Thu 26 Nov | **Channels WebSocket** tracking consumer + **`simulate_driver`** command + **SOS Bantay** + **Bagyo Mode** | 08 tracking-websockets, 09 sos, 10 bagyo-mode |
| 22 | Fri 27 Nov | Payment + wallet + receipt + payout (simulated gateway) — **FEATURE FREEZE at end of day** | 11 payment-wallet-receipt, 12 payout |

> **Phase 3's twelve step files do not exist yet, on purpose.** They are written around
> Day 14, once Phase 2 has settled — see
> [../../steps/phase-3-backend-api/00-overview.md](../../steps/phase-3-backend-api/00-overview.md)
> for the reasoning and the full step table. The numbers above are the filenames they
> will get: `steps/phase-3-backend-api/NN-name.md`.

### M4 — UI complete & integrated · Days 23–27 · 28 Nov – 2 Dec

| Day | Date | Deliverable | Step file |
|---|---|---|---|
| 23 | Sat 28 Nov | Vue 3 + Vite + Tailwind tokens + router + Pinia + axios with JWT interceptor | 01 vue-scaffold |
| 24 | Sun 29 Nov | Auth screens + shared components + API client + **`mock1_home.png`** — booking, mode grid, Isang Biyahe suggestion, Bagyo banner | 02 auth-screens, 03 shared-components, 04 api-client-stores, 05 home-booking-screen |
| 25 | Mon 30 Nov | **`mock2_tracking.png`** — Leaflet map, live driver position over WebSocket, driver card, SOS button | 06 tracking-screen |
| 26 | Tue 1 Dec | **`mock3_payment.png`** — fare breakdown, journey summary, rating, receipt download | 07 payment-receipt-screen |
| 27 | Wed 2 Dec | **`mock4_driver.png`** — request card, online toggle, earnings, accreditation — **UI FREEZE at end of day** | 08 driver-screen |

> Phase 4's eight step files are written around Day 22, when the API surface is frozen
> and each screen's data requirements are known rather than guessed — see
> [../../steps/phase-4-frontend/00-overview.md](../../steps/phase-4-frontend/00-overview.md).

### M5 — Tested, documented, submitted · Days 28–31 · 3–6 Dec

| Day | Date | Deliverable | Step file |
|---|---|---|---|
| 28 | Thu 3 Dec | End-to-end scenarios pass; persona UAT scripts run; bugs fixed | [phase-5](../../steps/phase-5-integration-testing/00-overview.md) |
| 29 | Fri 4 Dec | **Traceability matrix** complete; coverage report; final report drafted | [phase-6/01](../../steps/phase-6-documentation-submission/00-overview.md) |
| 30 | Sat 5 Dec | User manual, deployment guide, **demo video**, presentation deck | [phase-6](../../steps/phase-6-documentation-submission/00-overview.md) |
| 31 | Sun 6 Dec | Final commit, tag `v1.0.0`, submission checklist signed off, **SUBMITTED** | [phase-6](../../steps/phase-6-documentation-submission/00-overview.md) |

---

## 4. The working rhythm

A repeatable daily loop. It takes ten minutes and it is the difference between a
repo that documents a project and a repo that is just a folder of files.

1. **Start** — open [../../steps/PROGRESS.md](../../steps/PROGRESS.md), find today's
   step, read it end to end **before** typing anything.
2. **Build** — work the step. When you hit something the step did not anticipate,
   that is a finding: note it, do not silently work around it.
3. **Verify** — run the step's verification command. Every step has one. A step is
   not done because the code was written; it is done because the check passed.
4. **Log** — append to `steps/PROGRESS.md`: date, step, status, what actually
   happened, blockers, and the commit SHA.
5. **Commit** — one commit per step, using the convention in
   [phase-1/05](../../steps/phase-1-repository/05-workflow-conventions.md).
6. **Push** — always. A local-only commit is not a deliverable.

### Commit convention

```
<type>(<scope>): <what changed>

feat(rides): add Isang Biyahe trip chain endpoint
fix(pricing): apply surge multiplier before Pakyawan split
docs(stack): complete sections 3-5, fill channel layer rows
test(matching): cover the no-driver-available timeout
chore(repo): add gitignore and folder structure
```

Types: `feat` `fix` `docs` `test` `chore` `refactor` `style`.
Scopes: `repo` `stack` `db` `models` `rides` `pricing` `matching` `payments`
`tracking` `sos` `auth` `ui` `api` `docs`.

**Why this matters for CCS670:** a clean, well-messaged commit history is direct
evidence that you followed a process. It is graded, and it is free.

---

## 5. Scope ladder — what to cut, in order

The honest risk assessment: **7 features × 27 tables × 2 user roles in 27 days,
solo, is a large build.** The plan above is achievable but it has almost no slack.
If you fall behind, cut in this order — and cut early rather than hoping to catch up.

| Rung | Cut | Saves | Cost |
|---|---|---|---|
| 1 | **Bagyo Mode** → admin-settable multiplier only, no LGU trigger types, no auto-expiry | ~1 day | Minimal — the feature still demos |
| 2 | **SOS Bantay** → record the alert + notify contacts, drop the per-contact delivery tracking UI | ~0.5 day | Low — `SOS_NOTIFICATION` still written |
| 3 | **Driver screens** → merge into the passenger app's role-based routes, single page for requests + earnings | ~1 day | Low — `mock4` becomes one screen instead of four |
| 4 | **Frontend tests** → smoke tests only, no component coverage | ~1 day | Low — backend coverage carries the report |
| 5 | **`Saan ang Jeep?` live movement** → show the last known position with a refresh button instead of streaming | ~1.5 days | **Medium** — this is a signature feature; cut it only under duress |
| 6 | **Isang Biyahe** → cap chains at 2 legs | ~0.5 day | Low — the mechanism is identical |

**Never cut:** the 27-table schema, the fare calculator, the ride lifecycle, or the
traceability matrix. Those four are what the subject actually assesses.

### Hard stops

- **Day 22 (27 Nov) — FEATURE FREEZE.** No new features after this day, under any
  circumstance. Days 23–31 are for finishing, not adding.
- **Day 27 (2 Dec) — UI FREEZE.** Only bug fixes and copy changes after this.
- **Day 29 (4 Dec) — DOCUMENTATION FREEZE.** Everything must be written by end of
  this day; Day 30 is for the video and deck only.

---

## 6. Risk register

| # | Risk | Likelihood | Impact | Mitigation | Trigger to act |
|---|---|---|---|---|---|
| R1 | **Scope overrun** — 7 features is ambitious for 27 days solo | High | High | The scope ladder (§5); feature freeze Day 22 | You miss two consecutive days' deliverables |
| R2 | **Version pins don't resolve** (Vue Router 5 / Pinia 4 may not exist as pinned) | Medium | Medium | Run `pip install` and `npm install` on **Day 7**, not later. See stack review §5.1 | Install fails — drop the pin, take current, update the doc |
| R3 | **Python 3.14 wheel gap** for a compiled dependency | Low | Medium | Install every dependency in Phase 2; avoid Pillow by using emoji avatars | Any `pip install` tries to build from source |
| R4 | **Docker/Redis friction on Windows** | Medium | Medium | Docker Desktop installed and `docker compose up` proven on **Day 7** | Redis unreachable → fall back to polling (scope ladder rung 5 is independent of this) |
| R5 | **WebSocket debugging eats days** | Medium | High | Build the polling endpoint **first** as a fallback, then add Channels on top. The consumer becomes an optimisation, not a dependency | More than 4 hours lost to a connection that will not open |
| R6 | **Channels/DRF vs Django 6.1 incompatibility** | Low | High | Verify on Day 7 | `pip install` reports a Django ceiling |
| R7 | **Pricing rules from the mockups have no schema home** (audit finding A-13) | High | Medium | Decided in Step 0.01, recorded as **D-62**; implemented in Phase 2 Steps 02.01 and 02.03 | **CLOSED 11 Nov** — decision made; `RIDE_MODE.booking_fee` and `PLATFORM_CONFIG` land in Phase 2 |
| R8 | **The demo doesn't move** — nothing writes `TRIP_TRACKING` rows | High if unaddressed | High | Build `simulate_driver` on Day 21 | Demo day with a static map |
| R9 | **Illness / life event** — 31 days with no slack | Medium | High | The scope ladder, plus Days 30–31 are documentation only and can compress into one day if needed | Any lost day |
| R10 | **Over-polishing the UI** | Medium | Medium | UI freeze Day 27. The mockups are the spec — match them, don't exceed them | You are styling instead of building features |

---

## 7. Non-functional requirements — starter set

`technology_stack.md` and the concept paper define *what* the system does. Nothing
yet states *how well*. The final report needs this, and "fully functional" is
otherwise undefined. Proposed targets — adjust to what you actually achieve, and
report the measured number:

| Category | Requirement | Target | How to verify |
|---|---|---|---|
| Performance | Fare estimate response | < 500 ms p95 | Django Debug Toolbar / `pytest-benchmark` |
| Performance | Live position update latency | < 3 s end to end | Timestamp in the consumer vs. the browser |
| Performance | Page load, 4G | < 3 s | Chrome DevTools throttling |
| Capacity | Concurrent tracked rides | 10 | `simulate_driver` × 10 in parallel |
| Security | Passwords | Hashed, never logged | Code review; `password_hash` column |
| Security | API auth | JWT on every non-public endpoint | DRF permission classes |
| Security | Secrets | Never committed | `.gitignore` + `.env.example` only |
| Security | OTP | Rate-limited, TTL-expiring | Redis TTL; throttle class |
| Usability | Mobile viewport | 390 × 844 renders correctly | DevTools device toolbar |
| Usability | Time to book | ≤ 3 taps from home | Manual, against `mock1` |
| Reliability | Migrations | Idempotent, run clean on empty DB | Drop and re-migrate |
| Maintainability | Backend test coverage | ≥ 70% | `pytest --cov` |
| Portability | One-command environment | `docker compose up` | Fresh clone on Day 31 |

---

## 8. Definition of done

The project is complete when **all** of these are true. Print this. Tick it on
Day 31.

- [ ] `technology_stack.md` is complete — no truncated sections, no blank rows
- [ ] Root `README.md` explains the project to someone who has never seen it
- [ ] GitHub repository is public (or shared with the instructor) with full history
- [ ] `docker compose up` starts MySQL + Redis on a clean machine
- [ ] `python manage.py migrate` runs clean on an empty database
- [ ] All **27 tables** exist — proven by the schema-contract test, and readable in `docs/schema.sql`
- [ ] `seed_lookups` is idempotent and the lookup tables are populated
- [ ] All **7 features** are demonstrable end to end
- [ ] All **4 mockup screens** are live and match their designs
- [ ] Backend test suite green, coverage ≥ 70%
- [ ] `/api/docs/` Swagger UI renders and can drive a full ride
- [ ] **Traceability matrix** links requirement → use case → class → table → endpoint → screen → test
- [ ] Final report submitted
- [ ] User manual submitted
- [ ] Deployment / setup guide submitted
- [ ] Demo video recorded
- [ ] Presentation deck ready
- [ ] Git tag `v1.0.0` on the submitted commit
- [ ] `steps/PROGRESS.md` shows a complete, honest log of all 31 days

---

## 9. Next action

**Today, Day 5.** Open
[../../steps/phase-0-design-completion/00-overview.md](../../steps/phase-0-design-completion/00-overview.md)
and work the four steps in order. They finish the design phase and clear the path
to the repository tomorrow.
