# Step 0.01 — Complete the Technology Stack Document

| | |
|---|---|
| **Goal** | `docs/proposal/technology_stack.md` reads end to end — no truncated sections, no blank rows, no dangling cross-references — and the A-13 pricing gap is decided and recorded |
| **Day / Time** | Day 5 (Tue 10 Nov) · ~2 hours |
| **Prerequisites** | None. This is the first step of the build |
| **Produces** | Completed `technology_stack.md`; new entry D-62 in `database/consistency_report.md` |

---

## Before you start

Read [../../docs/review/01-technology-stack-review.md](../../docs/review/01-technology-stack-review.md)
first. It contains the recommended content for every section you are about to
write. This step tells you *how* to apply it; that document tells you *what*.

The document you are fixing is good work that stops mid-sentence. You are not
rewriting it — you are finishing it.

---

## Do this

### 1. Gather the real environment versions (~10 min)

Section 3 is titled *"Verify what is currently installed the system"* and is
empty. It was meant to carry the evidence for the document's opening claim that
everything was verified. Fill it with **actual output**, not recalled numbers.

From the project root in PowerShell:

```powershell
python --version
node --version
npm --version
git --version
java -version
docker --version
docker compose version
```

> `java -version` writes to stderr — that is normal, the output still shows. If
> `docker` is not recognised, Docker Desktop is not installed yet; that is a
> Phase 1 task, so write "not yet installed — see §7" and move on.

Copy the **literal output** into §3 as a fenced code block, with the date you ran
it. A version list with real output is evidence; a version list copied from the
table above it is not.

### 2. Write §3 — Verify what is currently installed (~20 min)

Replace the dangling heading `## 3. Verify what is currently installed the system`
(fix the word order — it reads "installed the system") with a complete section:

```markdown
## 3. Verify what is currently installed

Run on <11/11/2026 recorded verbatim.

```text
Python 3.14.9
v24.22.1
11.19.1
git version 2.56.0.windows.1
java version "22.0.1" 2024-04-16
Java(TM) SE Runtime Environment (build 22.0.1+8-16)
Java HotSpot(TM) 64-Bit Server VM (build 22.0.1+8-16, mixed mode, sharing)
docker : The term 'docker' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of the name, or if a path was included, 
verify that the path is correct and try again.
At line:6 char:1
+ docker --version
+ ~~~~~~
    + CategoryInfo          : ObjectNotFound: (docker:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
docker : The term 'docker' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of the name, or if a path was included, 
verify that the path is correct and try again.
At line:7 char:1
+ docker compose version
+ ~~~~~~
    + CategoryInfo          : ObjectNotFound: (docker:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
```

| Component | Required | Installed | Status |
|---|---|---|---|
| Python | 3.12–3.14 (Django 6.1 range) | 3.14.9 | ✅ |
| Node.js | ^20.19.0 \|\| >=22.12.0 (Vite 8) | 24.22.1 | ✅ |
| npm | — | 11.19.1 | ✅ |
| Git | — | 2.56.0 | ✅ |
| Java | 17+ (PlantUML) | <yours> | ✅ |
| Docker | — | <yours> | ⬜ Phase 1 |
| MySQL | 8.4+ (Django 6.1 floor) | via Docker | ⬜ Phase 1 |
| Redis | 7.x | via Docker | ⬜ Phase 1 |

Package-level verification (`pip install`, `npm install`) is recorded in §7.
```

Every row must say either a real version or an honest ⬜ with the phase that will
resolve it. **No blanks.**

### 3. Write §4 — the `PyMySQL[rsa]` explanation (~20 min)

Line 44 says *"Install as `PyMySQL[rsa]` (see §4)"* and §4 does not exist. Write it,
using §8 of the stack review as your source. It must cover:

- MySQL 8.4 defaults to `caching_sha2_password`
- PyMySQL is pure Python, so it has no OpenSSL bindings
- It therefore cannot complete the RSA key exchange over a non-TLS connection
- The `rsa` extra pulls in `cryptography`, which supplies it
- The exact error you get without it:

```
pymysql.err.OperationalError: (2061, 'Authentication plugin
'caching_sha2_password' reported error: Authentication requires secure connection.')
```

- The resulting pin: `PyMySQL[rsa]==1.2.3`

This is a genuinely good piece of engineering reasoning — the kind of thing that
reads well in a submitted document. Write it properly rather than as a footnote.

### 4. Write §5 — the frontend rationale (~20 min)

Line 34 says *"See §5"* and §5 does not exist. Write the section the table was
pointing at, covering:

- **Why Vue 3 over React or Svelte** — gentlest learning curve of the majors, and
  Single-File Components map 1:1 onto the four mockup screens (one `.vue` file per
  screen)
- **Why Vite** — first-party Vue integration; the dev server and the build are the
  same tool
- **Why Tailwind over a component library** — the mockup palette (`#1f4e79`,
  `#eef5fb`) is reproducible with utility classes; a component library would fight
  it
- **Why Leaflet + OpenStreetMap** — free and keyless, so no billing account and
  nothing to sign up for
- **Why one application with role-based routes** rather than two apps (stack review
  §6.1) — this is a decision you made on Day 5; record it here

### 5. Fill the two blank rows (~5 min)

Lines 47–48. Use stack review §3.1 and §3.2:

| Component | Technology | Version | Why this choice |
|---|---|---|---|
| **Channel layer** | `channels_redis` → Redis 7 | pin at install | The only officially maintained channel layer for Channels 4.x. `InMemoryChannelLayer` cannot cross processes, so it breaks as soon as `daphne` runs more than one worker |
| **Cache / channel backend** | `django-redis` → same Redis instance, db 1 | pin at install | One container, two logical namespaces. `LocMemCache` is per-process; `DatabaseCache` writes to MySQL on every read |

Add a short note under the table explaining the two-database-index choice (channel
layer on `/0`, cache on `/1`), and why `utf8mb4` is mandatory — the Tagalog UI
strings and the emoji mode icons in `mock1` cannot be stored in MySQL's legacy
3-byte `utf8`.

### 6. Add the missing rows (~20 min)

Stack review §7 is a **drop-in replacement for the whole §2 table** with the new
rows already marked **＋** and the filled blanks marked **✎**. Either paste it
wholesale, or add the ＋ rows individually — whichever you find easier to review.

The new rows are: ASGI server (`daphne`), containers (Docker Desktop + Compose),
geospatial (`geopy`), backend testing (`pytest` + `pytest-django` + `pytest-cov` +
`factory-boy`), frontend testing (`vitest` + `@vue/test-utils`), lint/format Python
(`ruff`), lint/format JS (`eslint` + `prettier` + `eslint-plugin-vue`), CI (GitHub
Actions), driver simulator, seed data, diagram tooling, SMS/OTP (simulated).

> **Do not invent version numbers for the new rows.** Write "pin at install" and
> resolve them in Phase 1 Step 06. An invented pin is worse than an honest
> placeholder, because it looks verified when it is not.

### 7. Add §6 — Considered and rejected (~15 min)

From stack review §4.5. Record what you deliberately did **not** add and why:
Celery, `mysqlclient`, native MySQL UUID columns, Dockerising Django itself, a
component library, `vue-i18n`.

This section is worth writing. Your `consistency_report.md` is strong precisely
because it records rejected alternatives alongside fixes; the stack document should
match that standard. It also pre-empts the question "why didn't you use X?"

### 8. Add §7 — Version verification (~5 min now, filled in Phase 1)

A stub section, to be completed on Day 7 when you actually run the installers:

```markdown
## 7. Version verification

`pip install -r backend/requirements.txt` and `npm install` in `frontend/` were run
on <date>. Output recorded verbatim in `docs/plan/install-log.txt`.

| Package | Pinned | Resolved | Note |
|---|---|---|---|
| (fill in Phase 1) | | | |
```

### 9. Fix the opening claim (~5 min)

The intro asserts that *"Every pinned version below was confirmed to exist in its
public registry"* and that compatibility *"was checked against each project's
declared metadata, not assumed."*

That is a strong, checkable claim, and §3 was evidently meant to carry the evidence
for it — which is exactly why the truncated section is a problem. Once §3 and §7
are written, the claim becomes true. Until then, soften it to something you can
stand behind:

> *Versions below were pinned against each project's public registry as of
> 6 November 2026. Sections 3 and 7 record the environment and install verification
> performed on the development machine.*

Then, after Phase 1, tighten it back if the installs confirm everything.

### 10. Decide the A-13 pricing gap (~20 min)

Read [../../docs/review/00-folder-audit.md](../../docs/review/00-folder-audit.md) §5.
Four pricing behaviours are shown in the mockups but cannot be stored or computed
by the 26-table design as it stands:

| Mockup shows | Problem |
|---|---|
| `Booking fee ₱3.00` | No column anywhere |
| `No commission on first 5 trips` | No commission rate, no promo trigger |
| Chain legs cheaper than standalone (₱22 vs ₱25; ₱17 vs ₱30) | No rule explains the discount |
| `₱144.00 − ₱96.00 + ₱3.00 = ₱48.00` | **Arithmetic does not close** — should be ₱51.00 |

`FareCalculator` has only `computeFare(leg, pax)` and `applyPakyawanSplit(fare, pax)`.
It cannot produce any of these.

**Recommended resolution** (cheapest path that keeps the mockups honest):

1. **Booking fee** — add `RIDE_MODE.booking_fee DECIMAL(8,2) NOT NULL DEFAULT 0`.
   It is a per-mode flat fee, so it belongs on the mode row.
2. **Commission waiver** — keep commission as a `PLATFORM_CONFIG` key-value table
   and implement the first-5-trips waiver as a documented business rule in
   `FareCalculator`. No schema change.
3. **Chain discount** — **drop it.** Make in-chain legs cost the same as standalone
   and correct the mockup. Simpler and more defensible than inventing a discount
   rule you would then have to justify.
4. **Fix the mockup arithmetic** — either correct the total to ₱51.00 or move the
   booking fee outside the "You paid" line.

Then record the outcome as **D-62** in `database/consistency_report.md`, appended to
the defect register in the same format as D-01…D-61. The existing report is
valuable because every change is traceable; keep that property intact.

> **Decided 11 November 2026 — all four recommendations taken.** D-62 is recorded in
> `database/consistency_report.md` §3.10. Two consequences to carry into Phase 2:
>
> - The design now has **27 tables**, not 26. `schema_listing.md` and the EER diagrams
>   are updated in Phase 2, Step 02.01, **before** the first migration.
> - `RIDE_MODE.booking_fee` lands in Phase 2, **Step 02.03** (that step writes
>   `RIDE_MODE` first so `Vehicle.mode` can resolve) — not Step 04.
>
> D-62 stays `decided` until Phase 2 implements it; then its status field becomes
> `implemented (Phase 2)`. Do not issue a second D-number for A-13.

---

## Verify

```powershell
# 1. No truncation — the file must end with a complete section, not a bare heading
Get-Content "docs\proposal\technology_stack.md" -Tail 15

# 2. No blank table cells
Select-String -Path "docs\proposal\technology_stack.md" -Pattern '\|\s*\|\s*\|'

# 3. Every cross-reference resolves — list the section headings
Select-String -Path "docs\proposal\technology_stack.md" -Pattern '^##+ '
```

Then read the whole document top to bottom once. **The check that matters is that
you can follow it as an instruction**: could someone who has never seen this project
install the stack from this document alone? If they would hit a section that isn't
there, it isn't done.

- [ ] §3 has real recorded output, not recalled numbers
- [ ] §4 exists and explains the `rsa` extra
- [ ] §5 exists and covers the frontend choices
- [ ] Both blank rows are filled
- [ ] All ＋ rows added, with "pin at install" where the version is unknown
- [ ] §6 records what was rejected and why
- [ ] §7 stub exists for the Phase 1 install log
- [ ] No dangling `see §N` references remain
- [ ] **D-62 recorded** in `database/consistency_report.md` §3.10, with its own row in
      the defect-register table and the four resolved behaviours spelled out
- [ ] `docs/review/00-folder-audit.md` A-13 marked **Resolved**, and its §5.1 note on
      the table count reading 27

---

## Log it

In [../PROGRESS.md](../PROGRESS.md), under **Session notes → Day 5**:

```markdown
### Day 5 — Tue 10 Nov

**Step 0.01 — technology stack document — DONE**

- Wrote §3 (environment verification), §4 (PyMySQL[rsa]), §5 (frontend rationale)
- Filled the channel-layer and cache-backend rows: channels_redis + django-redis,
  one Redis container, db 0 / db 1
- Added N new rows: daphne, Docker, geopy, pytest stack, vitest, ruff, eslint,
  GitHub Actions, simulate_driver, seed data, diagram tooling, simulated OTP
- Added §6 "Considered and rejected" — Celery, mysqlclient, native UUID, i18n
- Decided A-13: booking fee → RIDE_MODE.booking_fee; commission → PLATFORM_CONFIG
  rule; chain discount → dropped; mock3 arithmetic → corrected. Recorded as D-62.
- **Commit:** <sha>
```

Also tick the boxes in the master tracker and add the decision to the decision log.

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `docker` not recognised | Docker Desktop not installed | Expected on Day 5. Record "not yet installed — see §7" and install it in Phase 1 |
| `java -version` shows nothing | It writes to stderr | Run `java -version 2>&1` — or just confirm with `Get-Command java` |
| Unsure whether to add a package | You cannot say what it is for | Leave it out. Every row needs a reason in the last column; if you can't write one, it doesn't belong |
| Tempted to add Celery | It feels more "professional" | Re-read stack review §4.5. Nothing in this system needs an async worker, and a broker is a class of bug you cannot afford in 27 days |
| The A-13 decision feels like scope creep | It is — but it is scope you already promised in the mockups | Decide now, in one sitting, and move on. Undecided pricing discovered on Day 17 costs three days |
