# Phase 6 — Documentation and Submission

**Days 29–31 · 4–6 December 2026**
**Time budget: 3 days**

---

## Goal

The project is submitted: a final report, a user manual, a deployment guide, a demo
video, a traceability matrix, and a tagged `v1.0.0` build that an assessor can clone
and run.

---

## What this phase is worth

More than the calendar suggests. CCS670 assesses **software development**, and a
substantial part of that is whether the process is visible and the artefacts are
coherent. You have spent 28 days generating exactly that material — commit history,
design documents, a consistency audit, tests, step logs, a decision log. This phase
assembles it.

The mistake to avoid: treating these three days as paperwork to rush through. The
report is where a marker forms their judgment of the project. Three days of clear
writing about work you actually did converts 28 days of effort into a mark.

---

## Steps

| | Step | Day | What exists when it's done |
|---|---|---|---|
| ⬜ | 01 — Final report and traceability matrix | 29 | The report, with every requirement traced to a use case, a class, a table, an endpoint, a test and a commit |
| ⬜ | 02 — User manual | 30 | Passenger, driver and LGU walkthroughs with screenshots |
| ⬜ | 03 — Deployment guide | 30 | A fresh machine reaches a running system by following the README |
| ⬜ | 04 — Demo video and presentation deck | 30 | A 5–8 minute video covering all seven features; the deck for the defence |
| ⬜ | 05 — Submission checklist | 31 | Every submission requirement verified, not assumed |
| ⬜ | 06 — Final tag and handover | 31 | `v1.0.0` tagged, pushed, and the submission link confirmed working |

---

## The traceability matrix is the centrepiece

Everything else in this phase is documentation. The matrix is **evidence**.

It answers the question an assessor will ask in the defence: *"you claim you built
seven features from this design — show me the chain."* One row per requirement:

| Req | Use case | Class | Table | Endpoint | Test | Commit |
|---|---|---|---|---|---|---|
| Book a multi-mode ride | `UC_BookRide` | `MatchingEngine`, `FareCalculator` | `RIDE`, `RIDE_LEG`, `RIDE_MODE` | `POST /api/rides/` | `test_request_ride_*` | `a1b2c3d` |
| Chain multiple legs | `UC_ChainTrip` | `RideLeg` | `RIDE_LEG` | `POST /api/rides/{id}/legs/` | `test_chain_*` | `e4f5g6h` |
| Live driver tracking | `UC_TrackDriver` | `TripTrackingConsumer` | `TRIP_TRACKING` | `WS /ws/rides/{id}/` | `test_tracking_*` | `i7j8k9l` |
| Share a ride | `UC_Pakyawan` | `PakyawanGroup` | `PAKYAWAN_GROUP`, `FARE_SHARE` | `POST /api/pakyawan/` | `test_split_*` | `m0n1o2p` |
| LGU driver accreditation | `UC_AccreditDriver` | `Accreditation` | `ACCREDITATION`, `LGU_UNIT` | `POST /api/accreditations/` | `test_accredit_*` | `q3r4s5t` |
| Emergency SOS | `UC_RaiseSOS` | `SOSAlert` | `SOS_ALERT`, `SOS_NOTIFICATION` | `POST /api/sos/` | `test_sos_*` | `u6v7w8x` |
| Weather surge pricing | `UC_DeclareSurge` | `FareCalculator` | `SURGE_PERIOD` | `POST /api/surge/` | `test_surge_*` | `y9z0a1b` |

**A row with an empty cell is a finding, not a gap to hide.** If a requirement has no
test, either write the test or write down why not. An honest matrix with two documented
gaps is a stronger artefact than a complete-looking matrix that does not survive
checking — and the assessor will check.

Build this matrix in `steps/PROGRESS.md`, where a scaffold already exists from Phase 1.

---

## The deployment guide is tested by doing it

Do not write instructions from memory. **Clone the repository to a fresh folder and
follow your own README**, fixing it as you go.

```powershell
git clone https://github.com/<you>/sakay-ph.git "$env:TEMP\sakay-fresh"
Set-Location "$env:TEMP\sakay-fresh"
# now do exactly what the README says, and nothing else
```

Every step where you had to think "well obviously you also need to…" is a missing line.
This is the single highest-value hour of the phase: an assessor who cannot run the
project marks what they can see, not what you built.

**`docker compose down -v` before you start.** The guide must work from an empty
machine, which means an empty database.

---

## Milestone M5 exit criterion

> The repository is submitted, and a marker can clone it, run it in ten minutes, and
> find every artefact the brief asks for.

---

## What to submit

Confirm against your instructor's brief first — this is a default list, not a
substitute for reading the requirements.

| Artefact | Where it lives |
|---|---|
| Source code | GitHub repository, public (or the instructor invited to a private one) |
| Design documents | `docs/uml/`, `database/` |
| Final report | repository root or per the brief |
| User manual | repository root or per the brief |
| Deployment guide | `README.md` |
| Demo video | link in the README |
| Presentation deck | link in the README |
| Traceability matrix | `steps/PROGRESS.md` |
| Tagged release | `v1.0.0` |

---

## Watch out for

**Do not rewrite history.** Tempting at the end, and never worth it. A history with
some rough commits reads as real work; a suspiciously perfect one reads as staged.

**Do not let the video run long.** Five to eight minutes covering all seven features
beats twenty minutes of setup. Rehearse it once, record in one take, and if a feature
fails on camera, leave it in — a marker watching you diagnose a live issue learns more
than one watching a perfect run.

**Do not submit a private repository without confirming access.** A 404 is an
avoidable zero. `gh api repos/<you>/sakay-ph/collaborators` to check, or make it public.

**Do not leave the README describing an earlier state.** It was written on Day 7 and
updated on Day 19. Re-read it on Day 31 as though you were the marker.

**Documentation freeze is Day 29 for the report, but the README stays editable until
submission.** You will find a missing line on Day 31; fix it.

---

## After this phase

The project is done. Whatever remains unbuilt is a **documented limitation**, not a
failure — `docs/plan/design-freeze.md` has held that list since Day 5, and the honest
version of it is one of the strongest things you can hand an assessor.

Next: nothing. Submit.
