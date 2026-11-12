# Phase 5 — Integration and Testing

**Day 28 · Thursday 3 December 2026**
**Time budget: 1 day**

---

## Goal

Prove the whole system works together, end to end, as a person would use it — and fix
what that reveals.

---

## Why one day is enough, and why it is not optional

Phases 2 and 3 tested units: does the constraint hold, does the fare add up, does the
split balance. Phases 4 tested nothing, because a screen either renders or it does not
and you noticed immediately.

**Nobody has yet tested the seams.** Every integration defect lives in the gap between
two things that each work alone:

| Seam | The failure that lives there |
|---|---|
| Django ↔ Vue | A serializer returns `final_fare` as a string; the template renders `"60.00"` where a number was expected |
| Vue ↔ WebSocket | The consumer broadcasts to a group the client never joined |
| Auth ↔ everything | The access token expires mid-flow and the interceptor retries with the *refresh* token as the access token |
| Money ↔ UI | The Pakyawan split is correct in the database and displayed as `33.33333333` |
| Time ↔ display | A UTC timestamp rendered without conversion shows a ride ending before it started |

Every one of those passes its unit test and fails in front of a marker. That is what
this day is for.

---

## Steps

| | Step | Day | What exists when it's done |
|---|---|---|---|
| ⬜ | 01 — End-to-end scenarios | 28 | Seven scripted journeys, one per feature, each run against the real stack and recorded |
| ⬜ | 02 — Persona UAT scripts | 28 | A written script per persona (passenger, driver, LGU/barangay) with expected results |
| ⬜ | 03 — Bug fixing and regression | 28 | Every defect found above either fixed and retested, or logged as a known limitation |

---

## The seven scenarios

One per feature. Run them in this order — each depends on the previous one's data
being in place.

| # | Feature | The journey |
|---|---|---|
| 1 | **Lahat ng Sakyan** | Register → book a tricycle → matched → tracked → completed → paid |
| 2 | **Isang Biyahe** | Book a three-leg chain (tricycle → jeepney → UV Express); confirm the legs are ordered and the fares total |
| 3 | **Saan ang Jeep?** | Start `simulate_driver`; confirm the map dot moves without a page reload |
| 4 | **Pakyawan** | Three passengers join one group; confirm each is charged an equal share and the shares total the fare |
| 5 | **Sertipikadong Manong** | A driver registers → LGU accreditation is recorded → badge shows as verified |
| 6 | **SOS Bantay** | Raise an SOS mid-ride; confirm the position is snapshotted and every trusted contact is notified |
| 7 | **Bagyo Mode** | Declare a surge window; book during it; confirm the multiplier is applied **and recorded on the leg** |

Scenario 7's second half is the one people miss. Applying a surge is easy. Recording
*which* surge priced a leg is what makes the fare explainable a week later, and it is
a design decision from Phase 2 being tested.

---

## Milestone M5 (part one) exit criterion

> A person who has never seen the project can follow the seven scenarios and get the
> same results you did.

That is a written-documentation bar as much as a testing bar. A scenario that only
works because you know to click the third button first has not passed.

---

## How to run a scenario honestly

**Record what you did, not what you meant to do.**

```markdown
### Scenario 3 — Saan ang Jeep?

**Setup:** seeded database; ride 4f2a… in ONGOING; `simulate_driver` running.

| # | Action | Expected | Actual | Pass |
|---|---|---|---|---|
| 1 | Open /track/4f2a… | Map centres on the pickup | Map centred on pickup | ✓ |
| 2 | Wait 10s | Driver marker moves toward dropoff | Marker moved ~40m | ✓ |
| 3 | Stop `simulate_driver` | Marker stops; no error in console | Marker stopped; console clean | ✓ |
| 4 | Reload the page | Latest position restored from the API | Marker at the last ping | ✓ |

**Defects found:** none.
**Notes:** the marker jumps rather than animating between pings — cosmetic, logged as L-04.
```

Four things make that record worth having: the **setup** so it is reproducible, the
**actual** column so it is a test rather than a wish, the **pass/fail** so it can be
counted, and the **notes** so a cosmetic issue is distinguished from a defect.

---

## Watch out for

**Do not fix defects in this phase by changing the test.** If the split displays
`33.33333333`, the bug is in the serializer's decimal formatting, not in the
expectation.

**Do not start new features.** The scope ladder in `docs/plan/02-roadmap.md` is
explicit: after Day 27 you fix and document, you do not build.

**Do not skip the driver and LGU personas.** Testing only as a passenger leaves the
driver screen and the accreditation flow unverified, and they are two of the seven
features.

**Log cosmetic issues separately.** A jittering map marker and a wrong fare are not
the same severity, and a report that treats them alike reads as if you cannot tell
them apart.

---

## The step files

Written as the phase approaches, once Phase 4 has produced screens to test against.

Next: **Phase 6 — Documentation and Submission** · Days 29–31 · [../phase-6-documentation-submission/00-overview.md](../phase-6-documentation-submission/00-overview.md)
