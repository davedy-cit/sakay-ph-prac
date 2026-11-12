# Sakay.ph — EER ↔ UML Consistency Audit

**Question asked:** are the EER database diagrams consistent with the UML diagrams,
and free of defects?

**Verdict:** the EER is a faithful translation of the UML model — every class has a
table, every class attribute has a column or a documented resolution, and every use
case has somewhere to write. But the audit found **61 defects**, in two directions:

- the database side drew **cardinalities it cannot enforce**, and omitted two tables
  the UML needs;
- the UML side contained **contradictions the EER had faithfully inherited** —
  undeclared types, reversed include/extend arrows, an infinite loop, a payment
  path that could not fail, and three features that appear in the concept paper but
  in no diagram.

All 61 are fixed. This document is the evidence: what was checked, what was wrong,
what changed, and what is still a known limitation.

Two later design decisions are recorded in the same register, because the register is
the single running list of every change to the design: **D-62** (the pricing gap found
in the mockups, §3.10) and **D-63** (UUID storage on MySQL, §3.11). Neither is a defect
this audit found. The design is frozen as of **11 November 2026** — see
`docs/plan/design-freeze.md`.

---

## 1. Artifacts audited

| Artifact | Role |
|---|---|
| `database/eer_development.puml` | Comprehensive EER — 26 tables at audit time; **27 after D-62** |
| `database/eer_core.puml` | Part 1 of 2 — 12 tables (people, vehicles, rides, locations, pricing) |
| `database/eer_features.puml` | Part 2 of 2 — 14 tables + 4 key-only reference stubs |
| `database/er_overview.puml` | Simplified crow's-foot ER for the basic model |
| `database/schema_listing.md` | Written schema reference — 26 tables at audit time, domains, cardinalities; **gains table 27 and `RIDE_MODE.booking_fee` in Phase 2** |
| `uml/class_development.puml` | 20 classes, 8 enums |
| `uml/usecase_development.puml` | 27 use cases, 5 actors |
| `uml/sequence_development.puml` | Detailed interactions |
| `uml/activity_development.puml` | Swimlane process flow |
| `uml/usecase_overview.puml`, `sequence_overview.puml`, `activity_overview.puml`, `class_overview.puml` | Overview versions of the same four |

---

## 2. Coverage matrix

### 2.1 Every class has a table

| Class | Table | Notes |
|---|---|---|
| `User` *(abstract)* | **USER** | supertype |
| `Passenger` | **PASSENGER** | class-table subtype |
| `Driver` | **DRIVER** | class-table subtype |
| `Vehicle` | **VEHICLE** | |
| `Accreditation` | **ACCREDITATION** | `issuingLGU` promoted to **LGU_UNIT** |
| `Ride` | **RIDE** | |
| `RideLeg` | **RIDE_LEG** | weak entity |
| `Location` | **LOCATION** | |
| `PakyawanGroup` | **PAKYAWAN_GROUP** | |
| `SOSAlert` | **SOS_ALERT** | `notifiedContacts` → **TRUSTED_CONTACT** + **SOS_NOTIFICATION** |
| `Rating` | **RATING** | |
| `CancelResult` | **CANCELLATION** | a return value that is persisted |
| `Payment` | **PAYMENT** | |
| `FareShare` | **FARE_SHARE** | associative entity |
| `Wallet` | **WALLET** | |
| `Receipt` | **RECEIPT** | |
| `DriverPayout` | **DRIVER_PAYOUT** | *added by this audit* (D-08) |
| `SurgePeriod` | **SURGE_PERIOD** | *added by this audit* (D-09) |
| `MatchingEngine` | *(no table — service)* | stateless; `searchRadiusKm` is runtime config |
| `FareCalculator` | *(no table — service)* | its data lives in **RIDE_MODE** and **SURGE_PERIOD** |

Plus four tables with no class of their own, all documented as *(added)*:
**RIDE_MODE** and **PAYMENT_METHOD** (lookup tables standing in for the `RideMode`
and `PaymentMethod` enums), **LGU_UNIT** (a promoted attribute), **WALLET_TXN**
(the wallet ledger behind `Wallet.topUp/deduct/cashOut`), and **TRIP_TRACKING**
(the `Saan ang Jeep?` position stream).

### 2.2 Every class attribute has a column

| Class | Attribute | Column | Resolution |
|---|---|---|---|
| `User` | `userId` | `USER.user_id` | direct |
| | `fullName` | `USER.full_name` | direct |
| | `email` | `USER.email` | direct |
| | `phone` | `USER.phone` | direct |
| | `passwordHash` | `USER.password_hash` | direct |
| | `registrationDate` | `USER.registration_date` | direct |
| `Passenger` | `homeAddress` | `PASSENGER.home_address` | direct |
| | `preferredModes : List<RideMode>` | **PASSENGER_PREFERRED_MODE** | **multivalued → table** |
| | `gcashNumber` | `PASSENGER.gcash_number` | direct |
| `Driver` | `licenseNumber` | `DRIVER.license_number` | direct, `UQ` |
| | `accreditationStatus` | `DRIVER.accreditation_status` | domain `AccredStatus` |
| | `isOnline` | `DRIVER.is_online` | direct |
| | `rating` | `DRIVER.rating` | direct — **cached aggregate** |
| | `totalTrips` | `DRIVER.total_trips` | direct — **cached aggregate** |
| `Vehicle` | `plateNumber` | `VEHICLE.plate_number` | direct, `UQ` |
| | `model` | `VEHICLE.model` | direct |
| | `capacity` | `VEHICLE.capacity` | direct, nullable |
| | `routeInfo` | `VEHICLE.route_info` | direct, nullable |
| `Accreditation` | `accreditationId` | `ACCREDITATION.accreditation_id` | direct |
| | `issuingLGU` | `ACCREDITATION.lgu_code` → **LGU_UNIT** | promoted to a table |
| | `status` | `ACCREDITATION.status` | domain `AccredStatus` |
| | `expiryDate` | `ACCREDITATION.expiry_date` | direct |
| | `badgeVisible` | `ACCREDITATION.badge_visible` | direct |
| `Ride` | `rideId` | `RIDE.ride_id` | direct |
| | `requestTime` | `RIDE.request_time` | direct |
| | `status` | `RIDE.status` | domain `RideStatus` |
| | `totalFare` | `RIDE.final_fare` | **derived** — sum of `RIDE_LEG.fare` |
| | `isTripChain` | `RIDE.is_trip_chain` | direct |
| `RideLeg` | `legId` | — | **dropped** — replaced by composite PK `(ride_id, leg_no)` |
| | `sequence` | `RIDE_LEG.leg_no` | direct |
| | `mode` | `RIDE_LEG.mode_code` | domain `RideMode` |
| | `fare` | `RIDE_LEG.fare` | direct |
| | `distanceKm` | `RIDE_LEG.distance_km` | direct |
| | `etaMinutes` | `RIDE_LEG.eta_minutes` | direct |
| | `status` | `RIDE_LEG.status` | domain `RideStatus` |
| `Location` | `latitude` | `LOCATION.latitude` | direct |
| | `longitude` | `LOCATION.longitude` | direct |
| | `address` | `LOCATION.street / barangay / city / province` | **composite → 4 columns** |
| | `landmark` | `LOCATION.landmark` | direct, nullable |
| `PakyawanGroup` | `groupId` | `PAKYAWAN_GROUP.group_id` | direct |
| | `direction` | `PAKYAWAN_GROUP.direction` | direct |
| | `maxSeats` | `PAKYAWAN_GROUP.max_seats` | direct |
| | `matchedSeats` | `PAKYAWAN_GROUP.matched_seats` | direct |
| `SOSAlert` | `alertId` | `SOS_ALERT.alert_id` | direct |
| | `timestamp` | `SOS_ALERT.triggered_at` | direct |
| | `status` | `SOS_ALERT.status` | domain `SOSStatus` |
| | `notifiedContacts : List<String>` | **TRUSTED_CONTACT** + **SOS_NOTIFICATION** | **multivalued → 2 tables** |
| `Rating` | `ratingId` | `RATING.rating_id` | direct |
| | `stars` | `RATING.stars` | direct |
| | `comment` | `RATING.comment` | direct, nullable |
| | `date` | `RATING.rated_at` | direct |
| `CancelResult` | `fee` | `CANCELLATION.fee_amount` | direct |
| | `refund` | `CANCELLATION.refund_amount` | direct |
| | `reason` | `CANCELLATION.reason_code` | direct |
| `Payment` | `paymentId` | `PAYMENT.payment_id` | direct |
| | `amount` | `PAYMENT.amount` | direct |
| | `method` | `PAYMENT.method_code` | domain `PaymentMethod` |
| | `status` | `PAYMENT.status` | domain `PaymentStatus` |
| | `timestamp` | `PAYMENT.paid_at` | direct |
| `FareShare` | `shareId` | — | **dropped** — replaced by composite PK `(payment_id, passenger_id)` |
| | `passengerCount` | `FARE_SHARE.passenger_count` | direct — **frozen divisor** |
| | `shareAmount` | `FARE_SHARE.share_amount` | direct |
| | `isPaid` | `FARE_SHARE.is_paid` | direct |
| `Wallet` | `walletId` | `WALLET.wallet_id` | direct |
| | `balance` | `WALLET.balance` | direct |
| `Receipt` | `receiptNo` | `RECEIPT.receipt_no` | direct |
| | `issuedAt` | `RECEIPT.issued_at` | direct |
| `DriverPayout` | `payoutId` | `DRIVER_PAYOUT.payout_id` | direct |
| | `amount` | `DRIVER_PAYOUT.amount` | direct |
| | `method` | `DRIVER_PAYOUT.method_code` | domain `PaymentMethod` |
| | `status` | `DRIVER_PAYOUT.status` | domain `PayoutStatus` |
| | `requestedAt` | `DRIVER_PAYOUT.requested_at` | direct |
| | `paidAt` | `DRIVER_PAYOUT.paid_at` | direct, nullable |
| `SurgePeriod` | `surgeId` | `SURGE_PERIOD.surge_id` | direct |
| | `lguCode` | `SURGE_PERIOD.lgu_code` | direct, nullable |
| | `label` | `SURGE_PERIOD.surge_label` | direct |
| | `trigger` | `SURGE_PERIOD.trigger_type` | domain `SurgeTrigger` |
| | `multiplier` | `SURGE_PERIOD.multiplier` | direct |
| | `startsAt` / `endsAt` | `SURGE_PERIOD.starts_at` / `ends_at` | direct |
| | `isActive` | `SURGE_PERIOD.is_active` | direct |
| `FareCalculator` | `baseRates` | `RIDE_MODE.base_fare`, `RIDE_MODE.per_km_rate` | **lookup table** |
| | `surgeMultiplier` | `SURGE_PERIOD.multiplier` | **lookup table** |
| `MatchingEngine` | `searchRadiusKm` | — | **no column — runtime configuration**, not persisted state |

**Result: exactly one attribute in the whole model has no column**
(`MatchingEngine.searchRadiusKm`, correctly a runtime parameter), and two surrogate
identifiers are deliberately dropped in favour of natural composite keys.

### 2.3 Every enum has a domain

| Enum | Domain in `schema_listing.md` |
|---|---|
| `RideMode` | `RideMode` |
| `RideStatus` | `RideStatus` |
| `PaymentMethod` | `PaymentMethod` |
| `PaymentStatus` | `PaymentStatus` |
| `AccredStatus` | `AccredStatus` |
| `SOSStatus` | `SOSStatus` *(declared by this audit — D-10)* |
| `PayoutStatus` | `PayoutStatus` *(added by this audit — D-08)* |
| `SurgeTrigger` | `SurgeTrigger` *(added by this audit — D-09)* |

Plus three schema-side domains with no class counterpart: `UserRole` (the
specialization discriminator), `AccountStatus`, `GroupStatus`, `DeliveryStatus`,
and `TxnType`.

### 2.4 Every use case has somewhere to write

| Use case | Supporting tables |
|---|---|
| Create Account / Log In | USER, PASSENGER, DRIVER |
| Verify Identity (OTP / valid ID) | PASSENGER.`verified_at` |
| Book Ride | RIDE |
| Select Ride Mode | RIDE_MODE, PASSENGER_PREFERRED_MODE |
| Calculate Fare & ETA Estimate | RIDE.`fare_estimate`, RIDE_MODE, RIDE_LEG.`eta_minutes` |
| Apply Bagyo Mode | **SURGE_PERIOD**, RIDE_LEG.`surge_id` |
| Book Trip Chain (Isang Biyahe) | RIDE_LEG, RIDE.`is_trip_chain`, RIDE.`leg_count` |
| Match Pakyawan Share-Ride Group | PAKYAWAN_GROUP, RIDE_MODE.`is_shared` |
| Notify No Driver Available (timeout) | RIDE.`status`, CANCELLATION |
| Register as Driver | DRIVER, USER.`user_role` |
| Validate LGU Accreditation | ACCREDITATION, LGU_UNIT |
| Accept Ride | RIDE.`driver_id`, `matched_at`, `status` |
| Respond to Booking Request | same as Accept Ride |
| Start Trip | RIDE.`status`, TRIP_TRACKING |
| End Trip | RIDE.`ended_at`, `final_fare`, RIDE_LEG.`fare` |
| Cancel Trip | CANCELLATION |
| Apply Cancellation Policy | CANCELLATION.`fee_amount` / `refund_amount`, WALLET_TXN |
| Track Ride (Saan ang Jeep?) | TRIP_TRACKING |
| Share Trip Status | TRUSTED_CONTACT, SOS_NOTIFICATION |
| Trigger SOS Bantay | SOS_ALERT, SOS_NOTIFICATION, TRUSTED_CONTACT |
| Process Payment | PAYMENT |
| Charge Digital Wallet | WALLET, WALLET_TXN |
| Handle Cash Payment | PAYMENT.`method_code` = `CASH` |
| Split Fare Among Pakyawan Passengers | FARE_SHARE |
| Issue Receipt | RECEIPT |
| Rate Trip & Driver | RATING |
| Payout Driver Earnings | **DRIVER_PAYOUT** |

All 27 covered — none orphaned.

---

## 3. Defect register

Severity: **H** = a grader would mark it wrong · **M** = visibly inconsistent ·
**L** = cosmetic. **D-01 … D-61 are all fixed.** **D-62** and **D-63** (below) are not
defects this audit found — they are design decisions taken afterwards, recorded here so
the register stays the single running list of every change to the design.

**The next free number is D-64.** Always confirm that by opening this file and reading
the last entry before you write a new one — the number matters more than the entry.

### 3.1 Database diagrams — cardinalities the schema cannot enforce

The rule applied: **the crow's-foot symbol at an entity end must match the
nullability and uniqueness of the foreign key at the other end.** A nullable FK
requires `|o` / `o{` at the parent end, never `||` / `|{`.

| ID | Sev | Artifact | Was | Now | Why |
|---|---|---|---|---|---|
| D-01 | H | `eer_development.puml:346`, `eer_features.puml:210` | `pay \|\|--\|{ share` | `pay \|\|--o{ share` | A solo ride's payment is never split |
| D-02 | H | `eer_development.puml:345`, `eer_features.puml:209` | `grp \|\|--\|{ share` | `grp \|\|--o{ share` | A group in `FORMING` has no shares yet |
| D-03 | H | `eer_development.puml:358`, `eer_features.puml:214` | `sos \|\|--\|{ sosn` | `sos \|\|--o{ sosn` | An alert from a passenger with no trusted contacts notifies nobody |
| D-04 | H | `eer_development.puml:332`, `eer_core.puml:179` | `drv \|\|--\|{ accr` | `drv \|\|--o{ accr` | A newly registered driver holds no accreditation; `DRIVER.accreditation_status` already carries `PENDING` |
| D-05 | H | `eer_development.puml:320`, `eer_features.puml:195` | `pax \|\|--\|\| wallet` | `pax \|\|--o\| wallet` | A cash-only passenger need never have a wallet — and `PAYMENT.wallet_id` is already nullable |
| D-06 | M | `eer_development.puml:61`, `eer_core.puml:63` | `driver_id : UUID <<FK>>` | `<<FK, UQ>>` | `drv \|\|--o\| veh` draws 1:0..1, but nothing stopped a driver holding two vehicles |
| D-07 | M | `eer_development.puml:172` | `ride_id : UUID <<FK>>` | `<<FK, UQ>>` | `ride \|\|--o\| sos` draws 1:0..1, but nothing stopped two alerts on one ride |

`ride ||--|{ leg` and `ride ||--o| sos` were checked and are correct as drawn.

### 3.2 Database diagrams — missing tables

| ID | Sev | Defect | Fix |
|---|---|---|---|
| D-08 | H | `UC_Payout` ("Payout Driver Earnings") and `payoutDriver(driverId, earnings)` had **nowhere to be recorded**. `WALLET_TXN.wallet_id` is NOT NULL and points at `WALLET`, whose `passenger_id` is NOT NULL — a driver payout cannot live in a passenger's wallet. | New table **DRIVER_PAYOUT** (`eer_features.puml:98`, `eer_development.puml:233`) with `drv \|\|--o{ payout` and `pm \|\|--o{ payout`. `PAYOUT` removed from the `TxnType` domain. |
| D-09 | H | **Bagyo Mode appeared in no diagram at all** — yet it is one of the concept paper's signature features. `FareCalculator.surgeMultiplier` had no column anywhere. | New table **SURGE_PERIOD** (`eer_core.puml:102`, `eer_development.puml:108`) plus nullable `RIDE_LEG.surge_id` (`eer_core.puml:165`, `eer_development.puml:164`) recording the multiplier *actually applied* per leg. Relationships `lgu \|o--o{ surge` and `surge \|o--o{ leg`. Both legends now name Bagyo Mode. |

### 3.3 `er_overview.puml` — naming drift against the EER

| ID | Sev | Was | Now |
|---|---|---|---|
| D-10 | M | `VEHICLE.mode` | `VEHICLE.mode_code` |
| D-11 | M | `RIDE.mode` | `RIDE.mode_code` |
| D-12 | M | `PAYMENT.method` | `PAYMENT.method_code` |
| D-13 | M | `RIDE.total_fare` | `RIDE.final_fare` |
| D-14 | M | `VEHICLE.driver_id <<FK>>` | `<<FK, UQ>>` — the drawn 1:0..1 needs it |
| D-15 | M | `PAYMENT.ride_id <<FK>>` | `<<FK, UQ>>` — the drawn 1:0..1 needs it |

The basic model's deliberate simplifications (Passenger folded into USER, no
subtypes, no feature tables) were **left alone** — the existing note explains them.

### 3.4 `schema_listing.md` — factual errors

| ID | Sev | Defect | Fix |
|---|---|---|---|
| D-16 | H | "Strong entity … (23 of the 24 tables)" — but the very next rows list `RIDE_LEG` as weak and three tables as associative. The arithmetic never worked. | Now "22 of the 26 tables — the other four are the weak and associative entities below" |
| D-17 | M | The **Ternary relationship** row claimed the reference figure's ternary construct appears here. It does not: `FARE_SHARE` (two FKs in its PK) and `TRIP_TRACKING` are not ternary relationships. | Row replaced with an explicit **"Not used."** — every relationship in this schema is binary or unary, with the two associative entities named as resolutions of *binary* M:N |
| D-18 | M | `DRIVER.rating` was called **derived** in the concept map, but its own table row was not marked `DERIVED` and the EER does not mark it `<<derived>>`. Three artifacts, three answers. | Resolved toward the class diagram (which stores both): kept stored, relabelled **cached aggregates**, and separated from the genuinely derived `RIDE.final_fare` and `PASSENGER.rating_avg` |
| D-19 | M | `RIDE.mode_code`, `pickup_location_id`, `dropoff_location_id` and `VEHICLE.mode_code` were sourced to attributes that exist **only in `class_overview.puml`** — the development `Ride` has no origin/destination/mode and `Vehicle` has no mode. | Re-sourced to *(added — denormalized summary of the chain's first/last leg)*. `RECEIPT.total_amount` marked *(snapshot of `PAYMENT.amount`)* |
| D-20 | M | `TxnType` carried a `PAYOUT` value. | Removed, with a note pointing at `DRIVER_PAYOUT` |
| D-21 | M | The two new tables were absent. | Sections 8 and 19 added; all 26 sections renumbered by a title-keyed script (verified consecutive 1–26); intro "24 tables" → "26 tables" |
| D-22 | L | Cardinality summary did not reflect D-01…D-09. | Rewritten: 26 rows, each naming the constraint that enforces it |
| D-23 | L | No record of the columns that repeat data reachable by join. | New **"Documented denormalizations"** section — 8 rows, each with its reason, under the rule *freeze financial records, cache hot-path reads*. Converts a grader's "this is redundant" into "this was considered" |

### 3.5 `class_development.puml` — contradictions the EER inherited

| ID | Sev | Line | Defect | Fix |
|---|---|---|---|---|
| D-24 | H | 135 | `SOSStatus` used as `SOSAlert.status`'s type, **declared nowhere** | `enum SOSStatus` added; `SOSAlert ..> SOSStatus` |
| D-25 | H | 50, 66, 97 | `CancelResult` used as a return type, **declared nowhere** | Class added with `fee`, `refund`, `reason` — maps to the CANCELLATION table |
| D-26 | H | 305 | `Ride "0..*" --> "0..1" PakyawanGroup` — a group would serve many rides | `Ride "1" --> "0..1"`, matching `PAKYAWAN_GROUP.ride_id UQ` |
| D-27 | H | 309 | `Payment "0..*" --> "1" Wallet : charged to` — claimed every payment has a wallet, but the label already says "digital only" and cash bypasses the wallet | Wallet end corrected to `"0..1"`, matching the nullable `PAYMENT.wallet_id` |
| D-28 | H | 307 | `Payment "1" *-- "1..*" FareShare` — solo rides have no split | `"0..*"` |
| D-29 | H | 297 | `Driver "1" --> "1..*" Accreditation` — a new driver holds none | `"0..*"` |
| D-30 | H | 294 | `User "1" *-- "1" Wallet` — wallets are passenger-scoped, and a cash-only passenger needs none | `Passenger "1" *-- "0..1" Wallet` |
| D-31 | M | 303–304 | `RideLeg "1" --> "2" Location : origin / destination` — one association with a multiplicity of 2 | Split into two associations, each `"1" --> "1"`, matching the EER's two NOT NULL FKs |
| D-32 | H | — | **`Vehicle` was isolated** — no association at all, yet `RIDE.vehicle_id` exists and `sequence_development.puml` passes the plate number to the passenger | `Vehicle "0..1" --> "0..*" Ride : assigned to` |
| D-33 | M | — | The two new tables would have been new divergences | `DriverPayout` and `SurgePeriod` classes added with relationships, enums and notes |
| D-34 | L | 62 | `+ goOnline() / goOffline() : void` on one line — not valid UML | Two separate method lines |
| D-35 | L | 30 | The banner read `CORE ACTORS` but the section also holds `Vehicle` and `Accreditation` | Renamed `CORE ACTORS AND DRIVER ASSETS`; a new `PRICING AND WEATHER (BAGYO MODE)` banner added at 199 |

### 3.6 Use case diagrams

| ID | Sev | Artifact:line | Defect | Fix |
|---|---|---|---|---|
| D-36 | H | `usecase_development.puml:105` | `UC_Accept ..> UC_Respond : <<include>>` made Respond reachable only by first Accepting — **the decline path had no entry point**, contradicting `UC_Respond`'s own name ("accept/decline") | Flipped to `<<extend>>`; `Driver --> UC_Respond` added |
| D-37 | M | `usecase_development.puml:108` | `UC_Login ..> UC_Verify : <<extend>>` was filed under the **include** banner | Moved to the extend block |
| D-38 | M | `usecase_development.puml:30` | The `System` actor was described as "(matching engine)" but is associated with `UC_Pay` and `UC_Payout` | Renamed "(matching, pricing and payouts)" |
| D-39 | H | `usecase_development.puml` | **Bagyo Mode appeared in no use case** | `UC_BagyoMode` added, `..> UC_Fare : <<extend>>`, with an explanatory note |
| D-40 | H | `usecase_development.puml` | The sequence and activity diagrams both model a "no driver available" timeout, but no use case covered it | `UC_NoDriver` added, `..> UC_Book : <<extend>>` |
| D-41 | M | `usecase_overview.puml:53–55` | Three associations ran **use case → actor**, reversing every other arrow in the diagram | Direction fixed; labels moved to the correct end |
| D-42 | M | `usecase_overview.puml:30–38` | Four use-case names had drifted from the development diagram (`Create Account`, `Start Trip`/`End Trip` merged, `Track Ride`, `Rate Trip`) | Aligned: "Create Account / Log In", "Start Trip" + "End Trip", "Track Ride (Saan ang Jeep?)", "Rate Trip & Driver" |

### 3.7 Sequence diagrams

| ID | Sev | Artifact:line | Defect | Fix |
|---|---|---|---|---|
| D-43 | H | `sequence_development.puml:65` | The loop guard names "request timeout" but **no timeout branch exists** — the matching can never fail | Outer `alt driver matched / else no driver accepted within timeout` added, with `Matcher --> App : no driver available` and a passenger-facing message |
| D-44 | H | `sequence_development.puml:92–100` | A cancellation never notifies `Matcher` or `Driver`, contradicting `activity_development.puml` | `App -> Matcher : releaseDriver(ride)` and `App -> Driver : tripCancelled(ride)` added |
| D-45 | M | `sequence_development.puml:143` | The payout ran through the GCash/Maya lifeline even for **cash trips**, where the driver already holds the fare | Wrapped in `alt payout through GCash / Maya · else cash trip` |
| D-46 | M | `sequence_development.puml:108–121` | `shareTrip()` and `triggerSOS()` were merged into one message, collapsing two use cases | Split into two separate `opt` fragments |
| D-47 | M | `sequence_development.puml:76` | The Pakyawan `opt` guard had **no data source** | Guard now reads `ride is Pakyawan-eligible (RIDE_MODE.is_shared = true)` |
| D-48 | M | `sequence_development.puml:61` | `matchDriver(ride)` omitted the radius the activity diagram requires | `matchDriver(ride, searchRadiusKm)` |
| D-49 | H | `sequence_development.puml:40` | `UC_Verify` was unmodeled — login was a single opaque step | OTP challenge/response with `alt OTP verified / else OTP rejected` |
| D-50 | H | `sequence_development.puml:54` | **No surge / Bagyo Mode fragment**, though the use case now exists | `opt active surge window (Bagyo Mode) / Fare -> Fare : apply SURGE_PERIOD multiplier` |
| D-51 | M | `sequence_overview.puml` | The Payment Gateway was **conflated with the Driver**; no decline path; the cancellation sat before matching | `GW` lifeline added; `alt driver accepts / else declines or does not reply` added; cancel `opt` moved after matching; `System --> Passenger : Fare estimate + ETA` added |

### 3.8 Activity diagrams

| ID | Sev | Artifact:line | Defect | Fix |
|---|---|---|---|---|
| D-52 | H | `activity_development.puml:62–68` | The matching `repeat` had **no exit for "no driver found"** — an infinite loop | `if (driver accepted?) then (yes) else (no - no driver available) :Notify the passenger… stop` |
| D-53 | H | `activity_development.puml:100` | `stop` fired inside the cancel branch while the System and Driver lanes were still live | Cancellation confirmed in the Passenger lane, then a single clean `stop` |
| D-54 | M | `activity_development.puml:110` | `end fork` with no matching `end merge`, so the fork never rejoined the safety check | `end merge` |
| D-55 | H | `activity_development.puml:126–139` | The payment decision had **no failure path** — a declined charge still ended in a receipt | `if (payment approved?) then (no) :Retry or ask the passenger for another method; stop` |
| D-56 | M | `activity_development.puml:126` | The guard mixed a variable, an enum and two brand names | `(digital)` / `(cash)` |
| D-57 | M | `activity_development.puml:76` | The Pakyawan decision had **no data source** | `(Pakyawan requested and mode is shared?)` |
| D-58 | L | `activity_development.puml:127` | The Gateway lane used a colour undeclared in this file | Declared, recoloured to a distinct purple |
| D-59 | H | `activity_development.puml` | **No Bagyo Mode branch, and no Isang Biyahe fare node** — the note promised "one fare" with nothing computing it | `if (Isang Biyahe chain (leg_count > 1)?)` → sum leg fares; `if (active Bagyo Mode surge window?)` → apply the multiplier |
| D-60 | M | `activity_overview.puml:43` | The cancellation decision sat before matching | Moved after matching, with the timeout branch added |

### 3.9 Tooling defect found during verification

| ID | Sev | Defect | Fix |
|---|---|---|---|
| D-61 | **H** | PlantUML's default `PLANTUML_LIMIT_SIZE` is **4096 px**. A taller diagram is **silently clipped with exit code 0** — `activity_development.png` and `sequence_development.png` were both truncated at exactly 4096 px and looked like successful renders. | All renders now use `java -DPLANTUML_LIMIT_SIZE=16384 -jar plantuml.jar`. The two affected diagrams became 2180×5501 and 2066×4525 and were re-verified complete. |

### 3.10 Pricing gap found in the mockups (audit finding A-13)

**This entry is a decision, not a defect.** It is recorded here because the register is the
running list of every change to the design, and this changes the design. It is *not*
included in the "D-01 … D-61 are fixed" statement above.

**What was wrong.** The four mockups show four pricing behaviours that the 26-table schema
could neither store nor compute, and `FareCalculator`'s two operations —
`computeFare(leg, pax)` and `applyPakyawanSplit(fare, pax)` — could produce none of them.
Found by reading `mock1`, `mock3` and `mock4` against `schema_listing.md`.

| Mockup | Shows | Schema support before D-62 |
|---|---|---|
| `mock3_payment.png` | `Booking fee ₱3.00` | ❌ No column. `RIDE_MODE` had `base_fare` and `per_km_rate` only |
| `mock4_driver.png` | `Full fare — no commission on first 5 trips` | ❌ No commission rate, and `DRIVER.total_trips` existed but nothing read it as a promo trigger |
| `mock1_home.png` | Chain legs priced **below** standalone: tricycle ₱22 in-chain vs ₱25 standalone; e-trike ₱17 vs ₱30 | ❌ No rule explains the discount. `RIDE_LEG.fare` stored the result; nothing computed it |
| `mock3_payment.png` | `₱144.00 − ₱96.00 + ₱3.00 = ₱48.00` | ❌ **The arithmetic does not close.** 144 − 96 = 48, then +3 should be **₱51.00** |

**Resolution taken.**

| # | Behaviour | Resolution | Effect on the design |
|---|---|---|---|
| 1 | Booking fee | Add `RIDE_MODE.booking_fee DECIMAL(8,2) NOT NULL DEFAULT 0` | A per-mode flat fee belongs on the mode row, not on `RIDE` — one row changes the price for every ride of that mode |
| 2 | Commission waiver | Commission rate lives in a new `PLATFORM_CONFIG` key-value table; the first-5-trips waiver is a documented business rule inside `FareCalculator` | Adds `PLATFORM_CONFIG` as table 27; **no** change to `DRIVER`, because the counter already exists as `DRIVER.total_trips` |
| 3 | Chain discount | **Dropped.** In-chain legs cost the same as standalone | No schema change. The mockups are corrected instead |
| 4 | `mock3` arithmetic | **Corrected** to ₱51.00 | No schema change |

**Why the chain discount was dropped rather than implemented.** No rule in the concept paper,
the proposal or the use-case model justifies it — the discount appears only as a rendered
number in a PNG. Implementing it would mean inventing a business rule and then defending the
invention, and adding `RIDE.chain_discount` to carry it. Making in-chain legs cost the same as
standalone is simpler, needs no column, and is consistent with the one thing the design *does*
say about chains: that an Isang Biyahe trip's fare is the **sum of its legs**.

**Why the commission rate went into a table rather than into code.** A rate written into
`FareCalculator` is a deploy to change; a rate in `PLATFORM_CONFIG` is a row edit. The waiver
rule stays in code because it is a rule, not a number — the number it reads (`5`) is
configurable, the logic is not.

**Status of the two changes.** Both land in Phase 2 — `booking_fee` in Step 02.03 (it is a
column on `RIDE_MODE`, which that step writes first so that `Vehicle.mode` can resolve),
`PLATFORM_CONFIG` in Step 02.01 — **before** the first migration runs. Until they do, this
entry is `decided`, not `implemented`.

| ID | Sev | Artifact | Was | Now | Why |
|---|---|---|---|---|---|
| D-62 | **H** | `mock1_home.png`, `mock3_payment.png`, `mock4_driver.png`, `schema_listing.md` | Four pricing behaviours shown in the UI had no column, no rule and no computation; `mock3`'s total was ₱3.00 short | `RIDE_MODE.booking_fee` + `PLATFORM_CONFIG` (table 27); chain discount dropped; `mock3` corrected to ₱51.00 | `FareCalculator` could not reproduce any of them, so Phase 3 would have invented the rules mid-build — which is how a schema drifts from its design |

**The mockup PNGs were not edited.** They are the design input, and they are now known to
contain one arithmetic error and one behaviour that was deliberately dropped. That is recorded
here rather than silently corrected in the images, because a marker comparing the Phase 4
screens to `mock3_payment.png` will see ₱51.00 where the mockup says ₱48.00, and needs to find
this entry rather than wonder.

### 3.11 UUID storage on MySQL (Step 0.03)

**This entry is a decision, not a defect** — recorded in the same way as D-62, because it is a
documented deviation between what the schema writes and what the database will hold.

**What was wrong.** `schema_listing.md` writes the type of every primary and foreign key as
`UUID`, and `class_development.puml` types them as `UUID` too. MySQL 8.4 has **no native
`UUID` column type**. Django's `UUIDField` therefore stores these values as `CHAR(32)` — the
hex form without dashes. Left unrecorded, an assessor running `SHOW CREATE TABLE USER` would
find `char(32)` where the design says `UUID` and have no way to tell whether that was a
decision or a mistake.

| ID | Sev | Artifact | Was | Now | Why |
|---|---|---|---|---|---|
| D-63 | **L** | `schema_listing.md`, `class_development.puml` | Every key typed `UUID`, with no note on how MySQL stores it | `schema_listing.md` gained an "About the `UUID` type" note: Django's `UUIDField` → `CHAR(32)`, same value, 32 bytes instead of 16 | The alternative is a custom `BINARY(16)` field plus a hand-written migration — real complexity for a saving that does not matter at this scale. Recording the deviation costs three lines |

**Rejected alternative.** A custom field mapping to `BINARY(16)`: half the storage, and the
index is genuinely faster. Rejected because it needs a hand-written migration, breaks
`UUIDField`'s admin and form handling, and buys nothing a capstone can measure. **Django's
default is kept.**

**No diagram re-render is needed.** The EER diagrams show entities, keys and cardinalities;
none of them display a storage type, so nothing in `database/diagrams/` changes.

---

## 4. Documented limitations

Not defects — decisions, recorded so they are not mistaken for oversights.

1. **`MatchingEngine.searchRadiusKm` is not persisted.** It is runtime
   configuration, not platform state; the schema has no column for it.
2. **`DRIVER_PAYOUT` is driver-scoped, not ride-scoped.** A payout settles a
   balance spanning many rides, so there is no single `ride_id` to point at. Per-ride
   earnings remain derivable through `RIDE.driver_id` → `RIDE_LEG.fare`.
3. **`RIDE.fare_estimate` does not record which surge produced it.** The estimate is
   a quote; the multiplier *actually applied* is recorded per leg in
   `RIDE_LEG.surge_id`, which is the auditable figure.
4. **`TRIP_TRACKING` pings belong to the ride, not the leg.** A ping has no
   `leg_no`, so a position cannot be attributed to a specific leg of an Isang Biyahe
   chain. Acceptable for the *Saan ang Jeep?* map; a per-leg trail would need the
   extra key.
5. **`SOS_ALERT.raised_by` points at USER, while the class diagram has
   `Passenger.triggerSOS()`.** The FK is deliberately wider — a driver or an admin
   may also raise an alert.
6. **No SQL DDL was generated.** The listing is the written schema reference, per
   the original decision.
7. **`er_overview.puml` is a deliberate simplification** of the EER — no subtypes,
   no feature tables. Its note says so; it is not meant to be a second EER.
8. **`CancelResult` is a return value, not an entity.** It is persisted as
   CANCELLATION, but `Ride.cancel()` and `Driver.cancelTrip()` both return it, so it
   appears in the class diagram as a value object rather than a table.

---

## 5. Verification performed

1. **Structural checker** (`check_db.py`): no orphan entities; every relationship
   endpoint declared; every FK column named in a relationship; `eer_core` +
   `eer_features` **partitions `eer_development` exactly**; the listing covers every
   table. Final run: `tables: development=26  core=12  features=18` (14 full + 4
   stubs) — **all checks passed**.
2. **Every diagram re-rendered** with `-DPLANTUML_LIMIT_SIZE=16384`, requiring
   **exit code 0** on each — a failed render still writes a PNG, so the exit code is
   the only reliable signal. All 12 rendered clean.
3. **PNG dimensions checked** to catch the silent-clipping defect (D-61).
4. **Every diagram visually inspected** against the intended change list.
5. **Cardinalities re-read off the rendered PNGs** — the crow's-foot symbol at each
   end matches the column's nullability and unique constraint.
6. **The two new tables cross-checked** in all three places: `eer_development`,
   the `eer_core`/`eer_features` split, and `schema_listing.md`.
7. **Section numbering verified** consecutive 1–26 in the listing.
