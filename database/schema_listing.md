# Sakay.ph — Database Schema Listing

Companion reference for the ER / EER diagrams. Every table below appears in
`eer_development.puml`; `eer_core.puml` and `eer_features.puml` together contain
exactly the same 26 tables with the same column names.

**How to read a table:** *Key* shows `PK` (primary key), `FK` (foreign key), `UQ`
(unique) and `DERIVED` (computed, not stored). *Source* traces the column back to
the attribute it came from in `docs/uml/class/class_development.puml`, or says
*(added)* when the column was introduced by this database design and has no
class-diagram counterpart.

**About the `UUID` type.** Every primary key and foreign key below is written as
`UUID`. MySQL 8.4 has no native `UUID` column type, so Django's `UUIDField` stores
these as **`CHAR(32)`** — the 32-character hex form, no dashes. Same value, different
storage: 32 bytes instead of the 16 a `BINARY(16)` column would use. At this project's
scale the difference is immaterial, and the default avoids a custom field and a
hand-written migration. Recorded as **D-63** in `consistency_report.md` §3.11.

> ### ⚠ Pending: table 27 (`PLATFORM_CONFIG`) — D-62
>
> This listing currently describes the **26-table** design as audited. Audit finding
> **A-13** was decided on 11 November 2026 and recorded as **D-62** in
> `consistency_report.md` §3.10. It adds two things:
>
> 1. **`PLATFORM_CONFIG`** — a new key-value table (table 27) holding the commission
>    rate, the commission-free trip count, the cancellation fee and the SOS response
>    target
> 2. **`RIDE_MODE.booking_fee`** — a `DECIMAL(8,2) NOT NULL DEFAULT 0` column for the
>    flat per-mode booking fee the mockups show
>
> Both are written into this file in **Phase 2, Step 02.01** — *before* the first
> migration runs, because the design changes first and the code follows. Until that
> edit lands, this document and the EER diagrams deliberately still say 26.

---

## 1. USER

Supertype for every person on the platform — passengers, drivers and admins.

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| user_id | UUID | PK | — | `User.userId` |
| full_name | VARCHAR(120) | NOT NULL | — | `User.fullName` |
| phone | VARCHAR(15) | NOT NULL | — | `User.phone` |
| email | VARCHAR(120) | NULL | — | `User.email` |
| password_hash | VARCHAR(255) | NOT NULL | — | `User.passwordHash` |
| registration_date | DATE | NOT NULL | — | `User.registrationDate` |
| user_role | VARCHAR(12) | NOT NULL | domain `UserRole` | *(added — specialization discriminator)* |
| account_status | VARCHAR(12) | NOT NULL | domain `AccountStatus` | *(added)* |

## 2. PASSENGER — subtype of USER

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| passenger_id | UUID | PK, FK | USER.user_id | `Passenger` (subtype) |
| home_address | VARCHAR(255) | NOT NULL | — | `Passenger.homeAddress` |
| gcash_number | VARCHAR(15) | NOT NULL | — | `Passenger.gcashNumber` |
| verified_at | DATETIME | NULL | — | *(added — OTP / valid-ID verification)* |
| rating_avg | DECIMAL(2,1) | DERIVED | from RATING | *(derived)* |

> `Passenger.preferredModes : List<RideMode>` is a **multivalued attribute**; it is
> resolved into the `PASSENGER_PREFERRED_MODE` table (table 26).

## 3. DRIVER — subtype of USER

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| driver_id | UUID | PK, FK | USER.user_id | `Driver` (subtype) |
| license_number | VARCHAR(30) | NOT NULL, UQ | — | `Driver.licenseNumber` |
| accreditation_status | VARCHAR(12) | NOT NULL | domain `AccredStatus` | `Driver.accreditationStatus` |
| is_online | BOOLEAN | NOT NULL | — | `Driver.isOnline` |
| rating | DECIMAL(2,1) | NULL | — | `Driver.rating` *(cached aggregate of RATING)* |
| total_trips | INT | NOT NULL | — | `Driver.totalTrips` *(cached aggregate of completed RIDE rows)* |

## 4. VEHICLE

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| vehicle_id | UUID | PK | — | `Vehicle` |
| driver_id | UUID | NOT NULL, FK, UQ | DRIVER.driver_id | `Driver`–`Vehicle` (0..1) |
| mode_code | VARCHAR(12) | NOT NULL, FK | RIDE_MODE.mode_code | `RideMode` |
| plate_number | VARCHAR(12) | NOT NULL, UQ | — | `Vehicle.plateNumber` |
| model | VARCHAR(60) | NOT NULL | — | `Vehicle.model` |
| capacity | SMALLINT | NULL | — | `Vehicle.capacity` |
| route_info | VARCHAR(120) | NULL | — | `Vehicle.routeInfo` |

## 5. ACCREDITATION — Sertipikadong Manong

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| accreditation_id | UUID | PK | — | `Accreditation.accreditationId` |
| driver_id | UUID | NOT NULL, FK | DRIVER.driver_id | `Driver`–`Accreditation` (0..*) |
| lgu_code | VARCHAR(12) | NOT NULL, FK | LGU_UNIT.lgu_code | `Accreditation.issuingLGU` |
| badge_no | VARCHAR(20) | NOT NULL, UQ | — | *(added — printed badge)* |
| status | VARCHAR(12) | NOT NULL | domain `AccredStatus` | `Accreditation.status` |
| expiry_date | DATE | NOT NULL | — | `Accreditation.expiryDate` |
| badge_visible | BOOLEAN | NOT NULL | — | `Accreditation.badgeVisible` |

## 6. LGU_UNIT

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| lgu_code | VARCHAR(12) | PK | — | `Accreditation.issuingLGU` *(promoted to its own table)* |
| lgu_name | VARCHAR(80) | NOT NULL | — | *(added)* |
| province | VARCHAR(60) | NOT NULL | — | *(added)* |
| region | VARCHAR(40) | NOT NULL | — | *(added)* |
| contact_no | VARCHAR(20) | NULL | — | *(added)* |

## 7. RIDE_MODE — lookup

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| mode_code | VARCHAR(12) | PK | — | `RideMode` enum |
| mode_name | VARCHAR(30) | NOT NULL | — | `RideMode` enum |
| base_fare | DECIMAL(8,2) | NOT NULL | — | `FareCalculator.baseRates` |
| per_km_rate | DECIMAL(8,2) | NOT NULL | — | `FareCalculator.baseRates` |
| seat_capacity | SMALLINT | NOT NULL | — | *(added)* |
| is_shared | BOOLEAN | NOT NULL | — | *(added — Pakyawan-capable modes)* |

> Holds tricycle, jeepney, UV Express, habal-habal, e-trike and car — the
> *Lahat ng Sakyan* mode list.

## 8. SURGE_PERIOD — Bagyo Mode

A window during which a fare multiplier applies. One row per declared surge;
`RIDE_LEG.surge_id` records which one a leg was actually priced under.

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| surge_id | UUID | PK | — | *(added — Bagyo Mode)* |
| lgu_code | VARCHAR(12) | NULL, FK | LGU_UNIT.lgu_code | *(added)* |
| surge_label | VARCHAR(40) | NOT NULL | — | *(added — shown to the passenger)* |
| trigger_type | VARCHAR(12) | NOT NULL | domain `SurgeTrigger` | *(added)* |
| multiplier | DECIMAL(4,2) | NOT NULL | — | `FareCalculator.surgeMultiplier` |
| starts_at | DATETIME | NOT NULL | — | *(added)* |
| ends_at | DATETIME | NOT NULL | — | *(added)* |
| is_active | BOOLEAN | NOT NULL | — | *(added)* |

> `lgu_code` is nullable on purpose: a demand surge raised by the platform has no
> LGU behind it, while an LGU advisory or a typhoon declaration does.

## 9. PAYMENT_METHOD — lookup

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| method_code | VARCHAR(12) | PK | — | `PaymentMethod` enum |
| method_name | VARCHAR(30) | NOT NULL | — | `PaymentMethod` enum |
| is_digital | BOOLEAN | NOT NULL | — | *(added)* |
| gateway_name | VARCHAR(30) | NULL | — | *(added — GCash / Maya)* |

## 10. LOCATION

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| location_id | UUID | PK | — | `Location` |
| street | VARCHAR(120) | NOT NULL | — | `Location.address` *(composite)* |
| barangay | VARCHAR(60) | NOT NULL | — | `Location.address` *(composite)* |
| city | VARCHAR(60) | NOT NULL | — | `Location.address` *(composite)* |
| province | VARCHAR(60) | NOT NULL | — | `Location.address` *(composite)* |
| landmark | VARCHAR(120) | NULL | — | `Location.landmark` |
| latitude | DECIMAL(9,6) | NOT NULL | — | `Location.latitude` |
| longitude | DECIMAL(9,6) | NOT NULL | — | `Location.longitude` |

> `Location.address` is a **composite attribute**, split into its four parts above.

## 11. RIDE

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| ride_id | UUID | PK | — | `Ride.rideId` |
| passenger_id | UUID | NOT NULL, FK | PASSENGER.passenger_id | `Passenger`–`Ride` (books) |
| driver_id | UUID | NULL, FK | DRIVER.driver_id | `Driver`–`Ride` (drives) |
| vehicle_id | UUID | NULL, FK | VEHICLE.vehicle_id | *(added — the vehicle that served the ride)* |
| mode_code | VARCHAR(12) | NOT NULL, FK | RIDE_MODE.mode_code | *(added — denormalized summary of the chain's first leg)* |
| pickup_location_id | UUID | NOT NULL, FK | LOCATION.location_id | *(added — denormalized summary of the chain's first leg)* |
| dropoff_location_id | UUID | NOT NULL, FK | LOCATION.location_id | *(added — denormalized summary of the chain's last leg)* |
| status | VARCHAR(16) | NOT NULL | domain `RideStatus` | `Ride.status` |
| is_trip_chain | BOOLEAN | NOT NULL | — | `Ride.isTripChain` |
| leg_count | SMALLINT | NULL | — | *(denormalized count of RIDE_LEG rows)* |
| fare_estimate | DECIMAL(10,2) | NULL | — | `FareCalculator.computeFare` |
| final_fare | DECIMAL(10,2) | DERIVED | sum of RIDE_LEG.fare | `Ride.totalFare` *(derived)* |
| request_time | DATETIME | NOT NULL | — | `Ride.requestTime` |
| matched_at | DATETIME | NULL | — | *(added)* |
| ended_at | DATETIME | NULL | — | *(added)* |

## 12. RIDE_LEG — weak entity (Isang Biyahe)

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| ride_id | UUID | PK, FK | RIDE.ride_id | `Ride`–`RideLeg` *(identifying)* |
| leg_no | SMALLINT | PK | — | `RideLeg.sequence` |
| mode_code | VARCHAR(12) | NOT NULL, FK | RIDE_MODE.mode_code | `RideLeg.mode` |
| driver_id | UUID | NULL, FK | DRIVER.driver_id | *(added)* |
| origin_location_id | UUID | NOT NULL, FK | LOCATION.location_id | `RideLeg` origin |
| dest_location_id | UUID | NOT NULL, FK | LOCATION.location_id | `RideLeg` destination |
| fare | DECIMAL(10,2) | NOT NULL | — | `RideLeg.fare` |
| distance_km | DECIMAL(6,2) | NULL | — | `RideLeg.distanceKm` |
| eta_minutes | SMALLINT | NULL | — | `RideLeg.etaMinutes` |
| surge_id | UUID | NULL, FK | SURGE_PERIOD.surge_id | *(added — Bagyo Mode multiplier actually applied)* |
| status | VARCHAR(16) | NOT NULL | domain `RideStatus` | `RideLeg.status` |

> **Weak entity.** `RideLeg.legId` is replaced by the composite primary key
> `(ride_id, leg_no)` — a leg cannot be identified without its parent ride.

## 13. PAKYAWAN_GROUP

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| group_id | UUID | PK | — | `PakyawanGroup.groupId` |
| ride_id | UUID | NOT NULL, FK, UQ | RIDE.ride_id | `Ride`–`PakyawanGroup` (0..1) |
| direction | VARCHAR(120) | NOT NULL | — | `PakyawanGroup.direction` |
| max_seats | SMALLINT | NOT NULL | — | `PakyawanGroup.maxSeats` |
| matched_seats | SMALLINT | NOT NULL | — | `PakyawanGroup.matchedSeats` |
| group_status | VARCHAR(12) | NOT NULL | domain `GroupStatus` | *(added)* |

## 14. FARE_SHARE — associative entity

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| payment_id | UUID | PK, FK | PAYMENT.payment_id | `Payment`–`FareShare` *(split among)* |
| passenger_id | UUID | PK, FK | PASSENGER.passenger_id | `FareShare` → `Passenger` |
| group_id | UUID | NOT NULL, FK | PAKYAWAN_GROUP.group_id | `PakyawanGroup.splitFare` |
| passenger_count | SMALLINT | NOT NULL | — | `FareShare.passengerCount` |
| share_amount | DECIMAL(10,2) | NOT NULL | — | `FareShare.shareAmount` |
| is_paid | BOOLEAN | NOT NULL | — | `FareShare.isPaid` |

> **Associative entity** resolving the M:N between PAYMENT and PASSENGER.
> `FareShare.shareId` is replaced by the composite PK `(payment_id, passenger_id)`.

## 15. WALLET

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| wallet_id | UUID | PK | — | `Wallet.walletId` |
| passenger_id | UUID | NOT NULL, FK, UQ | PASSENGER.passenger_id | `Passenger` *-- `Wallet` (1:0..1) — passenger-scoped |
| balance | DECIMAL(12,2) | NOT NULL | — | `Wallet.balance` |
| currency | CHAR(3) | NOT NULL | — | *(added)* |
| updated_at | DATETIME | NOT NULL | — | *(added)* |

## 16. WALLET_TXN

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| txn_id | UUID | PK | — | *(added — wallet ledger)* |
| wallet_id | UUID | NOT NULL, FK | WALLET.wallet_id | `Wallet.topUp` / `deduct` / `cashOut` |
| payment_id | UUID | NULL, FK | PAYMENT.payment_id | *(added)* |
| txn_type | VARCHAR(12) | NOT NULL | domain `TxnType` | `Wallet` methods |
| amount | DECIMAL(10,2) | NOT NULL | — | *(added)* |
| balance_after | DECIMAL(12,2) | NOT NULL | — | *(added)* |
| gateway_ref | VARCHAR(40) | NULL | — | *(added)* |
| created_at | DATETIME | NOT NULL | — | *(added)* |

## 17. PAYMENT

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| payment_id | UUID | PK | — | `Payment.paymentId` |
| ride_id | UUID | NOT NULL, FK, UQ | RIDE.ride_id | `Ride`–`Payment` (1:1) |
| payer_id | UUID | NOT NULL, FK | PASSENGER.passenger_id | `Payment` payer |
| method_code | VARCHAR(12) | NOT NULL, FK | PAYMENT_METHOD.method_code | `Payment.method` |
| wallet_id | UUID | NULL, FK | WALLET.wallet_id | `Payment` → `Wallet` *(digital only)* |
| amount | DECIMAL(10,2) | NOT NULL | — | `Payment.amount` |
| gateway_ref | VARCHAR(40) | NULL | — | *(added)* |
| status | VARCHAR(16) | NOT NULL | domain `PaymentStatus` | `Payment.status` |
| paid_at | DATETIME | NOT NULL | — | `Payment.timestamp` |

## 18. RECEIPT

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| receipt_no | VARCHAR(20) | PK | — | `Receipt.receiptNo` |
| payment_id | UUID | NOT NULL, FK, UQ | PAYMENT.payment_id | `Payment`–`Receipt` (0..1) |
| total_amount | DECIMAL(10,2) | NOT NULL | — | `Payment.amount` |
| issued_at | DATETIME | NOT NULL | — | `Receipt.issuedAt` |
| receipt_url | VARCHAR(255) | NULL | — | `Receipt.download` |

> A ride is reachable through `payment_id → PAYMENT.ride_id`, so a separate
> `ride_id` column here would be redundant and is deliberately omitted.

## 19. DRIVER_PAYOUT

The driver-earnings ledger — the counterpart of PAYMENT, which collects from the
passenger. A payout cannot be a `WALLET_TXN` row, because `WALLET` is
passenger-scoped, so driver earnings get a table of their own.

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| payout_id | UUID | PK | — | *(added — Payout Driver Earnings)* |
| driver_id | UUID | NOT NULL, FK | DRIVER.driver_id | `Driver.requestPayout` |
| method_code | VARCHAR(12) | NOT NULL, FK | PAYMENT_METHOD.method_code | *(added — GCash / Maya)* |
| amount | DECIMAL(10,2) | NOT NULL | — | `Driver.requestPayout` |
| gateway_ref | VARCHAR(40) | NULL | — | *(added)* |
| status | VARCHAR(12) | NOT NULL | domain `PayoutStatus` | *(added)* |
| requested_at | DATETIME | NOT NULL | — | *(added)* |
| paid_at | DATETIME | NULL | — | *(added)* |

> Added by this design: `UC_Payout` and `payoutDriver(driverId, earnings)` in
> `uml/sequence_development.puml` previously had no table to write to.

## 20. SOS_ALERT — SOS Bantay

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| alert_id | UUID | PK | — | `SOSAlert.alertId` |
| ride_id | UUID | NOT NULL, FK, UQ | RIDE.ride_id | `Ride`–`SOSAlert` (0..1) |
| raised_by | UUID | NOT NULL, FK | USER.user_id | *(added)* |
| alert_type | VARCHAR(20) | NOT NULL | — | *(added)* |
| alert_lat | DECIMAL(9,6) | NOT NULL | — | *(added)* |
| alert_long | DECIMAL(9,6) | NOT NULL | — | *(added)* |
| status | VARCHAR(12) | NOT NULL | domain `SOSStatus` | `SOSAlert.status` |
| triggered_at | DATETIME | NOT NULL | — | `SOSAlert.timestamp` |
| resolved_at | DATETIME | NULL | — | `SOSAlert.resolve` |

## 21. TRUSTED_CONTACT

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| contact_id | UUID | PK | — | `SOSAlert.notifiedContacts` *(multivalued → table)* |
| passenger_id | UUID | NOT NULL, FK | PASSENGER.passenger_id | `Passenger` |
| contact_name | VARCHAR(120) | NOT NULL | — | *(added)* |
| contact_mobile | VARCHAR(15) | NOT NULL | — | *(added)* |
| relationship | VARCHAR(30) | NULL | — | *(added)* |

## 22. SOS_NOTIFICATION — associative entity

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| alert_id | UUID | PK, FK | SOS_ALERT.alert_id | `SOSAlert.notifiedContacts` |
| contact_id | UUID | PK, FK | TRUSTED_CONTACT.contact_id | `SOSAlert.notifiedContacts` |
| notified_at | DATETIME | NOT NULL | — | *(added)* |
| delivery_status | VARCHAR(12) | NOT NULL | domain `DeliveryStatus` | *(added)* |

> **Associative entity** resolving the M:N between SOS_ALERT and TRUSTED_CONTACT —
> the `notifiedContacts` list, with per-contact delivery state.

## 23. TRIP_TRACKING — Saan ang Jeep?

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| track_id | BIGINT | PK | — | *(added — live position pings)* |
| ride_id | UUID | NOT NULL, FK | RIDE.ride_id | `Ride`–`TripTracking` |
| latitude | DECIMAL(9,6) | NOT NULL | — | *(added)* |
| longitude | DECIMAL(9,6) | NOT NULL | — | *(added)* |
| recorded_at | DATETIME | NOT NULL | — | *(added)* |

## 24. CANCELLATION

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| cancel_id | UUID | PK | — | *(added — cancel trip use case)* |
| ride_id | UUID | NOT NULL, FK, UQ | RIDE.ride_id | `Ride`–`Cancellation` (0..1) |
| cancelled_by | UUID | NOT NULL, FK | USER.user_id | *(added)* |
| reason_code | VARCHAR(20) | NOT NULL | — | *(added)* |
| fee_amount | DECIMAL(10,2) | NOT NULL | — | *(added — cancellation policy)* |
| refund_amount | DECIMAL(10,2) | NOT NULL | — | *(added — cancellation policy)* |
| cancelled_at | DATETIME | NOT NULL | — | *(added)* |

## 25. RATING

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| rating_id | UUID | PK | — | `Rating.ratingId` |
| ride_id | UUID | NOT NULL, FK | RIDE.ride_id | `Ride`–`Rating` (0..*) |
| rater_user_id | UUID | NOT NULL, FK | USER.user_id | `Rating` → `Passenger` *(written by)* |
| ratee_user_id | UUID | NOT NULL, FK | USER.user_id | `Rating` → `Driver` *(about)* |
| stars | SMALLINT | NOT NULL | — | `Rating.stars` |
| comment | VARCHAR(255) | NULL | — | `Rating.comment` |
| rated_at | DATETIME | NOT NULL | — | `Rating.date` |

> **Unary / recursive relationship:** RATING points at USER twice — once for who
> wrote it, once for who it is about.

## 26. PASSENGER_PREFERRED_MODE

| Column | Type | Key | References | Source |
|---|---|---|---|---|
| passenger_id | UUID | PK, FK | PASSENGER.passenger_id | `Passenger.preferredModes` |
| mode_code | VARCHAR(12) | PK, FK | RIDE_MODE.mode_code | `Passenger.preferredModes` |
| preferred_rank | SMALLINT | NOT NULL | — | *(added — display order)* |

---

# Domains (enumerated values)

| Domain | Values | Source |
|---|---|---|
| UserRole | PASSENGER, DRIVER, ADMIN | *(added — specialization discriminator)* |
| AccountStatus | ACTIVE, SUSPENDED, DEACTIVATED | *(added)* |
| RideMode | TRICYCLE, JEEPNEY, UV_EXPRESS, HABAL_HABAL, ETRIKE, CAR | `RideMode` enum |
| RideStatus | REQUESTED, MATCHED, DRIVER_EN_ROUTE, ONGOING, COMPLETED, CANCELLED | `RideStatus` enum |
| PaymentMethod | GCASH, MAYA, CASH | `PaymentMethod` enum |
| PaymentStatus | PENDING, PROCESSING, COMPLETED, REFUNDED, FAILED | `PaymentStatus` enum |
| AccredStatus | PENDING, VERIFIED, EXPIRED, SUSPENDED | `AccredStatus` enum |
| SOSStatus | TRIGGERED, NOTIFIED, RESPONDING, RESOLVED, CANCELLED | `SOSStatus` enum |
| PayoutStatus | REQUESTED, PROCESSING, PAID, FAILED | `PayoutStatus` enum |
| SurgeTrigger | WEATHER, DEMAND, MANUAL, LGU_ADVISORY | `SurgeTrigger` enum |
| TxnType | TOPUP, DEDUCT, REFUND | *(added)* |
| GroupStatus | FORMING, FULL, DISPATCHED, COMPLETED, CANCELLED | *(added)* |
| DeliveryStatus | SENT, DELIVERED, FAILED | *(added)* |

> `TxnType` carries no `PAYOUT` value: a driver payout is not a passenger-wallet
> transaction, so it lives in `DRIVER_PAYOUT` (table 19) instead of `WALLET_TXN`.

---

# Cardinality summary

| Relationship | Cardinality | How it is enforced |
|---|---|---|
| USER → PASSENGER / DRIVER | 1 : 0..1 each, **disjoint + total** | `user_role` discriminator; subtype PK = FK to USER |
| PASSENGER → WALLET | 1 : 0..1 | `WALLET.passenger_id` NOT NULL + UQ (passenger-scoped; a cash-only passenger has none) |
| DRIVER → VEHICLE | 1 : 0..1 | `VEHICLE.driver_id` NOT NULL + UQ (each vehicle has exactly one driver) |
| DRIVER → ACCREDITATION | 1 : 0..* | `ACCREDITATION.driver_id` NOT NULL (a newly registered driver holds none yet) |
| LGU_UNIT → ACCREDITATION | 1 : 0..* | `ACCREDITATION.lgu_code` NOT NULL |
| LGU_UNIT → SURGE_PERIOD | 0..1 : 0..* | `SURGE_PERIOD.lgu_code` NULL (a platform demand surge has no LGU behind it) |
| PASSENGER → RIDE | 1 : 0..* | `RIDE.passenger_id` NOT NULL |
| DRIVER → RIDE | 0..1 : 0..* | `RIDE.driver_id` NULL until matched |
| RIDE → RIDE_LEG | 1 : 1..* | composite PK `(ride_id, leg_no)` — identifying |
| RIDE → PAYMENT | 1 : 0..1 | `PAYMENT.ride_id` NOT NULL + UQ |
| PAYMENT → RECEIPT | 1 : 0..1 | `RECEIPT.payment_id` NOT NULL + UQ |
| PAYMENT → WALLET | 0..1 : 0..* | `PAYMENT.wallet_id` NULL (cash payments bypass the wallet) |
| RIDE → PAKYAWAN_GROUP | 1 : 0..1 | `PAKYAWAN_GROUP.ride_id` NOT NULL + UQ |
| RIDE → SOS_ALERT | 1 : 0..1 | `SOS_ALERT.ride_id` NOT NULL + UQ |
| RIDE → CANCELLATION | 1 : 0..1 | `CANCELLATION.ride_id` NOT NULL + UQ |
| RIDE → RATING | 1 : 0..* | `RATING.ride_id` NOT NULL |
| RIDE → TRIP_TRACKING | 1 : 0..* | `TRIP_TRACKING.ride_id` NOT NULL |
| PAYMENT → FARE_SHARE | 1 : 0..* | `FARE_SHARE.payment_id` NOT NULL (a solo ride is never split) |
| PAKYAWAN_GROUP → FARE_SHARE | 1 : 0..* | `FARE_SHARE.group_id` NOT NULL (a `FORMING` group has no shares yet) |
| SOS_ALERT → SOS_NOTIFICATION | 1 : 0..* | `SOS_NOTIFICATION.alert_id` NOT NULL (no trusted contacts → nobody notified) |
| SURGE_PERIOD → RIDE_LEG | 0..1 : 0..* | `RIDE_LEG.surge_id` NULL (a leg priced outside any surge window) |
| DRIVER → DRIVER_PAYOUT | 1 : 0..* | `DRIVER_PAYOUT.driver_id` NOT NULL |
| PAYMENT_METHOD → DRIVER_PAYOUT | 1 : 0..* | `DRIVER_PAYOUT.method_code` NOT NULL |
| PASSENGER ↔ RIDE (Pakyawan) | M : N | resolved by **FARE_SHARE** |
| PAYMENT ↔ PASSENGER | M : N | resolved by **FARE_SHARE** |
| SOS_ALERT ↔ TRUSTED_CONTACT | M : N | resolved by **SOS_NOTIFICATION** |
| PASSENGER ↔ RIDE_MODE | M : N | resolved by **PASSENGER_PREFERRED_MODE** |
| USER → RATING (rater / ratee) | 1 : 0..* twice | unary relationship, two FKs to USER |

---

# EER concept map

Where each construct from the reference figures appears in this schema:

| EER construct | Where it lives |
|---|---|
| **Strong entity** | USER, RIDE, PAYMENT, LOCATION, VEHICLE, … (22 of the 26 tables — the other four are the weak and associative entities below) |
| **Weak entity** | RIDE_LEG — no identifier of its own, PK `(ride_id, leg_no)`, identifying relationship to RIDE |
| **Associative entity** | FARE_SHARE (PAYMENT × PASSENGER), SOS_NOTIFICATION (SOS_ALERT × TRUSTED_CONTACT), PASSENGER_PREFERRED_MODE (PASSENGER × RIDE_MODE) |
| **Supertype / subtype** | USER ⊂ PASSENGER, DRIVER — disjoint, total, discriminated by `user_role` |
| **Unary (recursive) relationship** | RATING → USER via `rater_user_id` and `ratee_user_id` |
| **Binary relationship** | Most of the schema (RIDE–PAYMENT, DRIVER–VEHICLE, …) |
| **Ternary relationship** | **Not used.** Every relationship in this schema is binary or unary. FARE_SHARE and SOS_NOTIFICATION are associative entities resolving *binary* M:N relationships, not ternary relationships; TRIP_TRACKING is an ordinary time-series child of RIDE. |
| **Identifier / partial identifier** | Each table's PK; RIDE_LEG's `ride_id` is the partial identifier owned by its parent |
| **Derived attribute** | RIDE.final_fare (sum of RIDE_LEG.fare), PASSENGER.rating_avg (averaged from RATING). DRIVER.rating and DRIVER.total_trips are **cached aggregates** — stored and refreshed rather than computed on read; see *Documented denormalizations*. |
| **Multivalued attribute** | `Passenger.preferredModes` → PASSENGER_PREFERRED_MODE; `SOSAlert.notifiedContacts` → TRUSTED_CONTACT + SOS_NOTIFICATION |
| **Composite attribute** | `Location.address` → street / barangay / city / province |
| **Optional attribute** | `email`, `landmark`, `capacity`, `route_info`, `comment`, `gateway_ref`, timestamps for match / end / resolve |
| **Lookup / reference table** | RIDE_MODE, PAYMENT_METHOD, LGU_UNIT, SURGE_PERIOD |

---

# Documented denormalizations

The columns below repeat something already reachable through a join. Each is kept
deliberately, for the reason given — these are design choices, not oversights.

| Column | Reachable via | Why it is kept |
|---|---|---|
| `RIDE.mode_code` | first leg's `mode_code` | The ride list and the *Lahat ng Sakyan* summary read one row, not the whole chain |
| `RIDE.pickup_location_id`, `RIDE.dropoff_location_id` | first / last leg's origin and destination | Same reason — the trip endpoints are the common query |
| `RIDE.leg_count` | `COUNT(RIDE_LEG)` | Cheap list rendering; the chain length shows before the legs load |
| `FARE_SHARE.group_id` | `payment_id → PAYMENT.ride_id → PAKYAWAN_GROUP` | Group-level totals without walking through PAYMENT |
| `FARE_SHARE.passenger_count` | `COUNT(FARE_SHARE)` for the payment | The divisor must be frozen at split time — a later count would change it |
| `RECEIPT.total_amount` | `PAYMENT.amount` | A receipt is an immutable financial snapshot; it must not move if the payment is later adjusted |
| `DRIVER.rating`, `DRIVER.total_trips` | aggregates over `RATING` / `RIDE` | Read on every match; recomputing per match is the expensive path |
| `PASSENGER.rating_avg` | average over `RATING` | Same hot path; marked `DERIVED` because it is refreshed from a single source |

> The rule applied throughout: **freeze anything that is a financial record**
> (receipt totals, split divisors) and **cache anything read on the hot path**
> (ratings, trip counts, leg counts).

---

# Design decisions worth noting

1. **Surrogate keys replaced by composite keys** where the relationship *is* the
   identity: RIDE_LEG `(ride_id, leg_no)`, FARE_SHARE `(payment_id, passenger_id)`,
   SOS_NOTIFICATION `(alert_id, contact_id)`, PASSENGER_PREFERRED_MODE
   `(passenger_id, mode_code)`. The class diagram's `legId` / `shareId` surrogates
   are dropped in favour of these natural keys.
2. **Class-table inheritance** for the USER specialization: subtypes share the
   supertype's primary key rather than duplicating its columns.
3. **No redundant `ride_id` in RECEIPT** — it is reachable through
   `payment_id → PAYMENT.ride_id`.
4. **Enumerations are stored as short VARCHAR codes** backed by the domains above,
   so new modes, payment methods or statuses can be added without a schema change.
5. **No SQL DDL was generated** — this listing is the written schema reference that
   accompanies the ER / EER diagrams.
6. **Two tables were added by this design** — `SURGE_PERIOD` (table 8) and
   `DRIVER_PAYOUT` (table 19). Bagyo Mode and *Payout Driver Earnings* appear in
   the concept paper and in the use-case / sequence diagrams but had no table to
   write to; `RIDE_LEG.surge_id` records the multiplier actually applied to a leg.
7. **Cardinalities state only what the schema can enforce.** Wherever a
   relationship is drawn 1 : 0..1, the "0..1" side carries a `UQ` constraint, so the
   drawing and the constraint agree. Where zero really is possible — a solo ride's
   fare split, a `FORMING` group's shares, a new driver's accreditation, a
   cash-only passenger's wallet — the drawing says `0..*` / `0..1` rather than
   claiming a mandatory row that no constraint guarantees.
