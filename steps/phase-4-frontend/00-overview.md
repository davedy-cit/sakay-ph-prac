# Phase 4 — Frontend

**Days 23–27 · 28 November – 2 December 2026**
**Time budget: 5 days**

---

## Goal

The four mockups exist as working screens, talking to the real API, over the real
WebSocket. A passenger can book a multi-mode trip and watch the driver move. A driver
can go online and accept a request.

---

## The four mockups are the specification

`docs/mockups/` holds four PNGs at 780×1688. **They are the acceptance criteria for
this phase**, and they were drawn before any code existed — which makes this phase a
translation exercise, not a design exercise.

| Mockup | Screen | Step |
|---|---|---|
| `mock1_home.png` | Booking, mode grid, Isang Biyahe suggestion, Bagyo banner | 05 |
| `mock2_tracking.png` | Leaflet map, live driver position, driver card, SOS button | 06 |
| `mock3_payment.png` | Fare breakdown, journey legs, rating, receipt | 07 |
| `mock4_driver.png` | Request card, online toggle, earnings, accreditation | 08 |

**Open the PNG next to the browser while you build.** Not from memory, and not from
the step file's description of it. The whole value of having drawn them is that this
phase requires no design decisions — so do not make any.

---

## Steps

| | Step | Day | What exists when it's done |
|---|---|---|---|
| ⬜ | 01 — Vue scaffold, Tailwind tokens and routing | 23 | Vue 3 + Vite + Tailwind 4 wired; router with role-based guards; Pinia; axios with a JWT interceptor |
| ⬜ | 02 — Auth screens | 24 | Login by phone, register, the simulated OTP entry |
| ⬜ | 03 — Shared components and design tokens | 24 | Buttons, cards, the mode chip, the status pill, the bottom sheet — used by every screen after this |
| ⬜ | 04 — API client and stores | 24 | One typed module per API area; auth and ride stores; error and loading handling that is not copy-pasted per screen |
| ⬜ | 05 — Home and booking screen | 24 | `mock1_home.png` |
| ⬜ | 06 — Tracking screen | 25 | `mock2_tracking.png` — Leaflet, live position over WebSocket, SOS |
| ⬜ | 07 — Payment and receipt screen | 26 | `mock3_payment.png` |
| ⬜ | 08 — Driver screen | 27 | `mock4_driver.png` |

**Titles, not links — the files are written around Day 22.** See the note at the end
of this file.

**Day 24 carries four steps.** Steps 02–05 are the bulk of the UI and they share one
sitting's worth of context: once the tokens, components and API client exist, each
screen is assembly. If Day 24 overruns, Step 05 slips to Day 25 morning and the
tracking screen follows — the mockup order is a priority order.

---

## Milestone M4 exit criterion

> The four screens match their mockups closely enough that a marker can put the PNG
> beside the browser and tick them off, **and every screen is driven by real API
> data.**

The second half is the one that matters. A screen that renders hardcoded JSON looks
identical to one that works. Prove it by restarting Django and reloading — if the
screen still shows data, it was hardcoded.

---

## Tailwind 4 is not Tailwind 3

This will cost you an hour if you do not know it. Tailwind 4 has **no
`tailwind.config.js`** and **no PostCSS configuration**. It is a Vite plugin.

```javascript
// frontend/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
})
```

```css
/* frontend/src/assets/main.css */
@import "tailwindcss";

@theme {
  --color-sakay-primary: #0F766E;
  --color-sakay-accent:  #F59E0B;
  --color-sakay-danger:  #DC2626;
}
```

Design tokens go in `@theme` inside CSS, not in a JavaScript config file. **Every
Tailwind 3 tutorial you find will tell you otherwise.** Follow the Tailwind 4
documentation, or the file you create will be ignored and the classes will do nothing.

---

## One Vue app, role-based routes

Decided in Phase 1 and recorded in the decision log: **one application, not two.**
Passenger and driver screens live in the same app behind a route guard.

```javascript
// frontend/src/router/index.js — the shape, not the final file
const routes = [
  { path: '/',              component: HomeView,       meta: { requiresAuth: true } },
  { path: '/track/:rideId', component: TrackingView,   meta: { requiresAuth: true } },
  { path: '/payment/:rideId', component: PaymentView,  meta: { requiresAuth: true } },
  { path: '/driver',        component: DriverView,     meta: { requiresAuth: true, role: 'DRIVER' } },
  { path: '/login',         component: LoginView,      meta: { guestOnly: true } },
]
```

Why one app: the driver and the passenger share the auth store, the API client, the
design tokens and the map component. Two apps would duplicate all four, and the
duplication would drift within a day.

---

## What Phase 3 left you that matters here

**Two environment variables, and only `VITE_`-prefixed ones reach the browser.**

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_WS_BASE_URL=ws://127.0.0.1:8000/ws
```

Without the `VITE_` prefix the value is `undefined` in the frontend and you will debug
it for an hour. This is the single most common Phase 4 mistake.

**CORS is already configured** for `localhost:5173` and `127.0.0.1:5173`. If a request
fails with a CORS error, the cause is that you are serving on a different port, not
that the setting is wrong.

**Derived fields need explicit serialization.** `ride.final_fare` and
`passenger.rating_avg` are properties, not columns. If the API response is missing
them, that is why — and the fix is in Phase 3's serializer, not in the Vue component.

---

## Watch out for

**Do not add a screen the mockups do not have.** An admin dashboard, a settings page,
a chat — each is a day that does not exist. The mockups are the scope.

**Do not use a component library.** Vuetify, PrimeVue or Element Plus would give you
a finished look in an hour, and it would look like every other Vue project. The
mockups have a specific visual language; Tailwind gets you there directly, and
matching a mockup is the graded skill.

**Do not hand-roll the map.** Leaflet with OpenStreetMap tiles is already in the
stack. No API key, no billing, no Google Maps.

**UI freeze is the end of Day 27.** After that, no visual changes. See
`docs/plan/02-roadmap.md`.

**Test on a phone-width viewport.** The mockups are 780×1688. A screen that only
works at 1440px does not match them.

---

## The step files

As with Phase 3, the eight step files will be written as the phase approaches —
around Day 22, when the API surface is frozen and each screen's data requirements are
known rather than guessed.

The day-by-day table above is the commitment.

---

## Next

**Phase 5 — Integration and Testing** · Day 28 · [../phase-5-integration-testing/00-overview.md](../phase-5-integration-testing/00-overview.md)
