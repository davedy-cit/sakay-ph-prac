# Sakay.ph — Isang App, Lahat ng Sakyan

A multi-mode ride-hailing platform for every Filipino transport mode.

**CCS670 — Object-Oriented Software Development · Capstone Project**
**[Vision Quest]** · Master in Information Technology · November–December 2026

---

## What this is

Ride-hailing in the Philippines serves two modes: cars and motorcycles. The vehicles most
commuters actually ride — **tricycle, habal-habal, jeepney, UV Express, e-trike and
car** — are booked by flagging them down, at a fare haggled in cash, with no record of
who drove.

Sakay.ph puts all six in one application. It books a single mode or **chains several into
one journey** with one fare and one receipt; matches **Pakyawan** share-rides and splits
the fare automatically; tracks jeepney and UV Express routes live; onboards
LGU-accredited drivers; raises an in-ride **SOS** to a passenger's trusted contacts; and
applies a weather-triggered fare multiplier during storms.

It is a solo capstone: a Django REST API over a 27-table MySQL schema, with a Vue 3
frontend. Payments, SMS and GPS are **simulated** — no real money moves and no real
gateway is called. The design decisions behind that, and every other limitation, are
listed in [`docs/plan/design-freeze.md`](docs/plan/design-freeze.md).

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

| Layer | Choice |
|---|---|
| Backend | Python 3.14 · Django 6.1 · Django REST Framework 3.18 |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Real-time | Django Channels 4.3 · Redis (via Docker) |
| Database | MySQL 8.4 (Docker) · `utf8mb4` |
| Frontend | Vue 3.5 · Vite · Tailwind CSS 4 · Pinia · Vue Router |
| Maps | Leaflet + OpenStreetMap |
| Testing | pytest · pytest-django · vitest · ruff |

Full reasoning, versions and the options that were rejected:
[`docs/proposal/technology_stack.md`](docs/proposal/technology_stack.md).

## Repository layout

```
ride-hailingSystem/
├── README.md                 ← this file
├── database/                 ← schema, diagrams, consistency audit
├── docs/
│   ├── proposal/             concept paper, proposal deck, technology stack
│   ├── uml/                  use case, class, sequence, activity diagrams
│   ├── mockups/              the four UI mockups
│   ├── review/               folder audit and technology stack review
│   └── plan/                 roadmap and design freeze
└── steps/                    ← the build manual
    ├── README.md
    ├── PROGRESS.md           ← master tracker, decision log, daily log
    └── phase-0…6/            one folder per phase
```

**Two things about this layout are deliberate.**

`database/` sits at the repository root rather than under `docs/`, because the schema is a
first-class artefact of an OO design course rather than supporting documentation. Roughly
thirty path references in `consistency_report.md` and `schema_listing.md` already point at
`database/...`; moving it would break every one for a cosmetic gain. It is documented
rather than tidied.

`steps/` is not documentation *about* the project — it is the working manual used to build
it, phase by phase, with a progress log and a decision log. `steps/PROGRESS.md` is the
honest record of what was done on which day.

**Phase 1 adds** `backend/`, `frontend/`, `docker-compose.yml`, `.gitignore` and
`.env.example`; Phase 2 adds `database/schema.sql`.

## Documentation

| Where | What |
|---|---|
| [`docs/proposal/`](docs/proposal/) | Concept paper, proposal deck, technology stack |
| [`docs/uml/`](docs/uml/) | Use case, class, sequence, activity diagrams (development + overview) |
| [`database/`](database/) | EER/ER diagrams, schema listing (26 tables as audited; 27 once D-62 lands), consistency audit |
| [`docs/mockups/`](docs/mockups/) | UI mockups — passenger and driver |
| [`docs/review/`](docs/review/) | Folder audit and technology stack review |
| [`docs/plan/`](docs/plan/) | Roadmap and design freeze |
| [`steps/`](steps/) | Build instructions and progress log |

## Running it

> **Not yet runnable.** Implementation begins 11 November 2026; setup instructions land in
> Phase 1.

This section is deliberately honest rather than aspirational. When `docker compose up` and
`npm run dev` actually work, they will be documented here with the exact commands.

## Status

| Milestone | Dates | Status |
|---|---|---|
| M1 — Design frozen & repository live | 6–12 Nov | 🟡 in progress |
| M2 — Database & domain model | 13–19 Nov | ⬜ |
| M3 — All 7 features via API | 20–27 Nov | ⬜ |
| M4 — UI complete & integrated | 28 Nov – 2 Dec | ⬜ |
| M5 — Tested, documented, submitted | 3–6 Dec | ⬜ |

The design is **frozen as of 11 November 2026** ([`docs/plan/design-freeze.md`](docs/plan/design-freeze.md)).
Full timeline and scope ladder: [`docs/plan/02-roadmap.md`](docs/plan/02-roadmap.md).
