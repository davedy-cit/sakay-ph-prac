# Phase 3 — Backend API

**Days 15–22 · 20–27 November 2026**
**Time budget: 8 days**

---

## Goal

All seven features work through the API. Every capability in the use-case diagram is
reachable over HTTP or WebSocket, protected by JWT, documented in Swagger, and
covered by tests. No UI yet.

---

## What this phase is actually about

Phase 2 built a database. Phase 3 builds the **domain logic** — and this is the phase
CCS670 is really assessing. The subject is Object-Oriented Software Development, so
the marks here are not for "an endpoint exists" but for whether the design patterns
from your class diagram survived contact with real code:

| Pattern | Where it appears | What it buys |
|---|---|---|
| **Service layer** | `FareCalculator`, `MatchingEngine` | Fare rules and matching rules live in one place, not scattered across views |
| **Adapter** | Simulated GCash/Maya gateway | Swapping in a real gateway is one class, not a rewrite |
| **Value object** | `CancelResult`, `FareBreakdown` | An operation returns a described outcome instead of mutating state and hoping |
| **Repository** | Django's ORM managers, custom querysets | Query logic named and reusable |
| **Strategy** | Per-mode fare rules | Adding a mode does not add a branch to `computeFare` |

**If you write fat views and thin services, you have missed the subject.** The
`FareCalculator` and `MatchingEngine` from `class_development.puml` must exist as real
classes with real methods, and the views must be thin wrappers over them. An assessor
comparing your class diagram to your code should find the classes.

---

## Steps

| | Step | Day | What exists when it's done |
|---|---|---|---|
| ⬜ | 01 — JWT auth and simulated OTP | 15 | Register (passenger + driver), login by phone, refresh; OTP stored in Redis with a TTL |
| ⬜ | 02 — Serializers, viewsets and Swagger | 16 | CRUD for the core entities; `/api/docs/` renders |
| ⬜ | 03 — FareCalculator | 17 | Base fare + per-km + booking fee + Pakyawan split + surge multiplier, unit tested |
| ⬜ | 04 — MatchingEngine | 18 | Radius search via geopy, accept/decline, **the no-driver timeout path** |
| ⬜ | 05 — Ride lifecycle and cancellation | 19 | Request → match → en route → ongoing → complete, plus the cancellation fee/refund policy |
| ⬜ | 06 — Isang Biyahe trip chain | 20 | Multi-leg booking; `RIDE_LEG` written in order; the chain totals |
| ⬜ | 07 — Pakyawan grouping | 20 | Group formation, seat capacity, `FARE_SHARE` splitting that sums exactly |
| ⬜ | 08 — Tracking WebSockets and `simulate_driver` | 21 | Channels consumer; `TRIP_TRACKING` written live; a driver that actually moves |
| ⬜ | 09 — SOS Bantay | 21 | Alert raised, position snapshotted, fan-out to trusted contacts |
| ⬜ | 10 — Bagyo Mode | 21 | Surge windows; the multiplier applied to a leg and recorded on it |
| ⬜ | 11 — Payment, wallet and receipt | 22 | Simulated gateway, wallet ledger, receipt issue |
| ⬜ | 12 — Driver payout | 22 | Earnings request and simulated disbursement |

**These are titles, not links — the files do not exist yet.** Each becomes a link to
`NN-name.md` in this folder as it is written, around Day 14. Until then there is
nothing to open, which is why nothing here is clickable.

**Days 20, 21 and 22 carry two to three steps each.** That is the roadmap's plan, not
an accident. By then the patterns are established and each step is largely mechanical.
If you fall behind, the scope ladder in `docs/plan/02-roadmap.md` says what to cut —
and it is never the fare calculator or the matching engine.

---

## Milestone M3 exit criterion

> **Every one of the seven features is demonstrable with `curl` or the Swagger UI.**
> Not "the code exists" — *demonstrable*, by someone who has not read your code.

Test it that way. Open `/api/docs/`, authenticate, and walk the seven features
without opening an editor. Any feature that needs you to explain which endpoint to
call first is not finished.

---

## The one hard rule of this phase

**Views are thin. Logic is in services.**

```python
# ✗ Wrong — the fare rule now exists in the view, and again in the
#   receipt generator, and again in the fare-preview endpoint.
class RideViewSet(viewsets.ModelViewSet):
    def create(self, request):
        fare = mode.base_fare + (distance * mode.per_km_rate)
        if surge:
            fare *= surge.multiplier
        ...

# ✓ Right — the view asks the domain, and the domain owns the rule.
class RideViewSet(viewsets.ModelViewSet):
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ride = RideService.request_ride(**serializer.validated_data)
        return Response(RideSerializer(ride).data, status=201)
```

This is the difference between a project that demonstrates OO design and one that
demonstrates Django. Both work. Only one is being graded.

---

## What Phase 2 left you that matters here

Three things from the previous phase shape this one:

**The composite keys are `UniqueConstraint`s, not primary keys.** So a `RideLeg`
serializer must treat `(ride, leg_no)` as the natural key and validate it, because
the ORM will not do it for you in a nested write.

**`AUTH_USER_MODEL` is `accounts.User`, keyed on phone.** SimpleJWT needs
`USER_ID_FIELD = "id"` and a token that carries the user id; the login view takes
`phone` and `password`, not `username` and `password`. This is the first thing to get
right in Step 01.

**`final_fare` and `Passenger.rating_avg` are derived properties, not columns.** A
serializer that lists model fields automatically will silently omit them. Every
serializer that needs them must declare them explicitly.

---

## The step files

Phases 0–2 have one file per step because they are behind you and their content is
settled. **Phase 3's twelve step files will be written as the phase approaches** —
around Day 14, when Phase 2's outcome is known.

That is a deliberate choice, not a gap. Phase 2 is already teaching things that will
change Phase 3: the exact shape of the composite-key validation, which model methods
turned out to be needed, and whether `PLATFORM_CONFIG` exists. Writing twelve detailed
step files now would mean rewriting several of them in a week.

What you have here is enough to plan against. The day-by-day table above is the
commitment; the detail follows.

---

## Watch out for

**Do not build a UI shortcut.** When a feature is hard to test with `curl`, the
temptation is a quick HTML page. That page becomes the thing you maintain, and Phase
4 rebuilds it properly in Vue. Use the Swagger UI instead.

**Do not put business rules in serializers.** A serializer validates input shape. The
moment it starts deciding a fare or choosing a driver, it has become a service with a
worse name.

**Do not skip the timeout path in Step 04.** The no-driver-available case is defect
D-43 from the consistency report — a design flaw the audit found and fixed on paper.
Step 04 is where the fix becomes real code, and it is exactly the kind of thing an
assessor probes.

**Do not let the WebSocket work run long.** Live tracking is the most visually
impressive feature and the easiest to over-invest in. `simulate_driver` moving a dot
along a route is sufficient and demonstrable.

**Feature freeze is the end of Day 22.** After that, no new endpoints. See
`docs/plan/02-roadmap.md` for the hard stops.

---

## Next

**Phase 4 — Frontend** · Days 23–27 · [../phase-4-frontend/00-overview.md](../phase-4-frontend/00-overview.md)
