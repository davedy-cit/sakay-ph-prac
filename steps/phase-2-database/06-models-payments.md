# Step 2.06 — Models: Payments

| | |
|---|---|
| **Goal** | PAYMENT_METHOD, WALLET, WALLET_TXN, PAYMENT, FARE_SHARE, RECEIPT and DRIVER_PAYOUT exist; a Pakyawan fare can be split across passengers and the split adds up to the fare |
| **Day / Time** | Day 13 (Wed 18 Nov) · ~3 hours |
| **Prerequisites** | [Step 2.05](05-models-rides-features.md) |
| **Produces** | `backend/apps/payments/models.py` |

---

## What makes this app different

Every other app stores what happened. This one stores **money**, and money has
different rules:

| Rule | Where it is enforced |
|---|---|
| A fare split must sum to the fare | Service layer (Phase 3) — a database CHECK cannot sum across rows |
| The split divisor is frozen at split time | `FARE_SHARE.passenger_count` is a column, not a count |
| A receipt is immutable | `RECEIPT.total_amount` is copied from the payment, not joined to it |
| A wallet balance cannot go negative | A CHECK constraint, backed by `select_for_update` in Phase 3 |

The first one is worth pausing on, because it is a genuine limitation of the design
and you should be able to explain it: **a relational CHECK constraint cannot assert
that a set of rows sums to a value in another table.** MySQL has no assertion
mechanism. So "the shares total the fare" is enforced in `FareCalculator`, and the
database enforces the pieces it can — each share is positive, the divisor is
positive, and no two shares collide.

Say that plainly in your report. It is the correct answer, and it shows you know
where your guarantees live.

---

## Do this

### 1. Write the payment models (~120 min)

Create `backend/apps/payments/models.py`:

```python
# backend/apps/payments/models.py
"""Payment-domain models: tables 9, 14-19 in database/schema_listing.md.

Every table that moves money lives here. The gateway is simulated — see
apps/core/constants.SIMULATED_GATEWAY_PREFIX — but the ledger is real, which
is what makes the wallet and payout behaviour demonstrable.
"""

import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.enums import PaymentMethod, PaymentStatus, PayoutStatus, TxnType


class PaymentMethodLookup(models.Model):
    """Lookup of accepted payment methods. Table 9."""

    method_code = models.CharField(
        max_length=12, primary_key=True, choices=PaymentMethod.choices
    )
    method_name = models.CharField(max_length=30)
    is_digital = models.BooleanField(
        default=True, help_text="False for cash, which bypasses the wallet."
    )
    gateway_name = models.CharField(max_length=30, blank=True)

    class Meta:
        db_table = "PAYMENT_METHOD"
        verbose_name = "payment method"
        verbose_name_plural = "payment methods"
        ordering = ["method_code"]

    def __str__(self) -> str:
        return self.method_name


class Wallet(models.Model):
    """A passenger's stored balance. Table 15.

    Passenger-scoped: 1 : 0..1, so ``passenger`` is NOT NULL + UNIQUE. A
    cash-only passenger simply has no wallet row.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    passenger = models.OneToOneField(
        "accounts.Passenger",
        on_delete=models.CASCADE,
        related_name="wallet",
        db_column="passenger_id",
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="PHP")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "WALLET"
        verbose_name = "wallet"
        verbose_name_plural = "wallets"
        constraints = [
            # The safety net for every money bug. A negative balance is
            # always a defect, never a legitimate state — refunds increase
            # the balance, and a deduction that would overdraw must be
            # rejected by the caller.
            models.CheckConstraint(
                condition=models.Q(balance__gte=0), name="ck_wallet_balance_nonneg"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.passenger.user.full_name}: ₱{self.balance}"

    @property
    def is_empty(self) -> bool:
        return self.balance == 0


class Payment(models.Model):
    """One payment for one ride. Table 17.

    ``ride`` is NOT NULL + UNIQUE: a ride has at most one payment (1 : 0..1).
    ``wallet`` is nullable because a cash payment never touches a wallet
    (PAYMENT -> WALLET is 0..1 : 0..*).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ride = models.OneToOneField(
        "rides.Ride", on_delete=models.PROTECT, related_name="payment", db_column="ride_id"
    )
    payer = models.ForeignKey(
        "accounts.Passenger",
        on_delete=models.PROTECT,
        related_name="payments_made",
        db_column="payer_id",
    )
    method = models.ForeignKey(
        PaymentMethodLookup,
        on_delete=models.PROTECT,
        related_name="payments",
        db_column="method_code",
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
        db_column="wallet_id",
    )

    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    # Populated by the simulated gateway adapter. Always prefixed SIM-.
    gateway_ref = models.CharField(max_length=40, blank=True)
    status = models.CharField(
        max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    paid_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "PAYMENT"
        verbose_name = "payment"
        verbose_name_plural = "payments"
        ordering = ["-paid_at"]
        indexes = [
            models.Index(fields=["status", "-paid_at"], name="idx_payment_status"),
            models.Index(fields=["payer", "-paid_at"], name="idx_payment_payer"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="ck_payment_amount_nonneg"
            ),
        ]

    def __str__(self) -> str:
        return f"₱{self.amount} ({self.method.method_name}, {self.status})"

    @property
    def is_settled(self) -> bool:
        return self.status == PaymentStatus.COMPLETED


class Receipt(models.Model):
    """An issued receipt. Table 18.

    ``receipt_no`` is the primary key — a human-readable document number,
    not a UUID, because a passenger reads it aloud to support.

    ``total_amount`` duplicates ``PAYMENT.amount`` on purpose: a receipt is
    an immutable financial snapshot and must not change if the payment is
    later adjusted. schema_listing.md lists this as a documented
    denormalization.
    """

    receipt_no = models.CharField(max_length=20, primary_key=True)

    payment = models.OneToOneField(
        Payment, on_delete=models.PROTECT, related_name="receipt", db_column="payment_id"
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    issued_at = models.DateTimeField(default=timezone.now)
    receipt_url = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "RECEIPT"
        verbose_name = "receipt"
        verbose_name_plural = "receipts"
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return f"Receipt {self.receipt_no} — ₱{self.total_amount}"

    @classmethod
    def next_receipt_no(cls) -> str:
        """Generate the next document number, e.g. ``SKY-20261118-0007``.

        Not safe under concurrency — two simultaneous payments could collide
        on the primary key. Acceptable for a single-developer demo; Phase 3
        notes the fix (a database sequence or a retry loop).
        """
        today = timezone.localdate().strftime("%Y%m%d")
        prefix = f"SKY-{today}-"
        last = (
            cls.objects.filter(receipt_no__startswith=prefix)
            .order_by("-receipt_no")
            .values_list("receipt_no", flat=True)
            .first()
        )
        seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
        return f"{prefix}{seq:04d}"


class FareShare(models.Model):
    """Associative entity: PAYMENT × PASSENGER. Table 14. Pakyawan.

    Resolves the M:N between PAYMENT and PASSENGER — who owes what on a
    shared ride. The documented key is ``(payment_id, passenger_id)``;
    uniqueness is enforced by a UniqueConstraint because Django has no
    composite primary key.

    ``passenger_count`` is stored rather than counted because the divisor
    must be frozen at split time. Counting later would change what an
    already-paid passenger owes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="shares", db_column="payment_id"
    )
    passenger = models.ForeignKey(
        "accounts.Passenger",
        on_delete=models.PROTECT,
        related_name="fare_shares",
        db_column="passenger_id",
    )
    # Denormalized: group-level totals without walking payment -> ride.
    group = models.ForeignKey(
        "rides.PakyawanGroup",
        on_delete=models.PROTECT,
        related_name="fare_shares",
        db_column="group_id",
    )

    passenger_count = models.SmallIntegerField(validators=[MinValueValidator(1)])
    share_amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    is_paid = models.BooleanField(default=False)

    class Meta:
        db_table = "FARE_SHARE"
        verbose_name = "fare share"
        verbose_name_plural = "fare shares"
        ordering = ["payment", "passenger"]
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "passenger"], name="uq_fareshare_payment_passenger"
            ),
            models.CheckConstraint(
                condition=models.Q(passenger_count__gte=1),
                name="ck_fareshare_count_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(share_amount__gte=0),
                name="ck_fareshare_amount_nonneg",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.passenger.user.full_name} owes ₱{self.share_amount}"


class WalletTxn(models.Model):
    """A wallet ledger entry. Table 16.

    Append-only: an entry is never edited, because the ledger is the audit
    trail. ``balance_after`` is stored so a statement can be printed without
    replaying every prior row.

    ``txn_type`` has no PAYOUT value — driver earnings are not a
    passenger-wallet transaction and live in DRIVER_PAYOUT instead.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    wallet = models.ForeignKey(
        Wallet, on_delete=models.PROTECT, related_name="transactions", db_column="wallet_id"
    )
    payment = models.ForeignKey(
        "Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallet_transactions",
        db_column="payment_id",
    )
    txn_type = models.CharField(max_length=12, choices=TxnType.choices)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    gateway_ref = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "WALLET_TXN"
        verbose_name = "wallet transaction"
        verbose_name_plural = "wallet transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "-created_at"], name="idx_txn_wallet_recent"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="ck_txn_amount_nonneg"
            ),
            models.CheckConstraint(
                condition=models.Q(balance_after__gte=0), name="ck_txn_balance_nonneg"
            ),
        ]

    def __str__(self) -> str:
        sign = "+" if self.txn_type == TxnType.TOPUP else "−"
        return f"{sign}₱{self.amount} ({self.txn_type})"


class DriverPayout(models.Model):
    """Driver earnings ledger. Table 19.

    The counterpart of PAYMENT, which collects from the passenger. Added by
    the database design: ``UC_Payout`` and ``payoutDriver(driverId,
    earnings)`` in the sequence diagram previously had no table to write to.

    Cannot be a WALLET_TXN row, because WALLET is passenger-scoped.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    driver = models.ForeignKey(
        "accounts.Driver",
        on_delete=models.PROTECT,
        related_name="payouts",
        db_column="driver_id",
    )
    method = models.ForeignKey(
        PaymentMethodLookup,
        on_delete=models.PROTECT,
        related_name="payouts",
        db_column="method_code",
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    gateway_ref = models.CharField(max_length=40, blank=True)
    status = models.CharField(
        max_length=12, choices=PayoutStatus.choices, default=PayoutStatus.REQUESTED
    )
    requested_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "DRIVER_PAYOUT"
        verbose_name = "driver payout"
        verbose_name_plural = "driver payouts"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["driver", "status"], name="idx_payout_driver_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="ck_payout_amount_nonneg"
            ),
        ]

    def __str__(self) -> str:
        return f"₱{self.amount} to {self.driver.user.full_name} ({self.status})"

    @property
    def is_settled(self) -> bool:
        return self.status == PayoutStatus.PAID
```

**Why `WalletTxn.payment` is `SET_NULL` while `FareShare.payment` is `CASCADE`.**
A fare share has no meaning without its payment — delete the payment and the split
is gone. A wallet ledger entry is history: a top-up is still a top-up even if the
payment row it referenced is later removed. `PROTECT` on `WalletTxn.wallet` goes the
other way — you cannot delete a wallet that has ledger entries, because that would
destroy the audit trail.

**`on_delete=PROTECT` almost everywhere else.** In a payments app, `PROTECT` is the
default posture. Deleting a payment method that 200 payments used should fail loudly,
not cascade.

### 2. Register the app's models for the admin later (~2 min)

Nothing to do now — Step 08 handles admin registration for all apps at once.

### 3. Migrate (~15 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
python manage.py makemigrations payments
python manage.py migrate
```

`makemigrations` may warn about the `Payment` ↔ `WalletTxn` ordering. It resolves
itself because both are string references inside one app.

### 4. Prove a Pakyawan split adds up (~45 min)

The split arithmetic is the part most likely to be wrong, and this is the last
chance to catch it before it is buried under an API. In `manage.py shell`:

```python
from decimal import Decimal, ROUND_HALF_UP
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Driver, Passenger, User
from apps.core.enums import PaymentMethod, PaymentStatus, RideMode, RideStatus, UserRole
from apps.payments.models import (
    DriverPayout, FareShare, Payment, PaymentMethodLookup, Receipt, Wallet, WalletTxn,
)
from apps.rides.models import Location, PakyawanGroup, Ride, RideLeg, RideModeLookup
from apps.core.enums import TxnType

# ── Lookups ────────────────────────────────────────────────────
gcash, _ = PaymentMethodLookup.objects.get_or_create(
    method_code=PaymentMethod.GCASH,
    defaults=dict(method_name="GCash", is_digital=True, gateway_name="GCash"))
cash, _ = PaymentMethodLookup.objects.get_or_create(
    method_code=PaymentMethod.CASH,
    defaults=dict(method_name="Cash", is_digital=False))

tricycle = RideModeLookup.objects.get(mode_code=RideMode.TRICYCLE)
a = Location.objects.create(street="A", barangay="Poblacion", city="Cabuyao",
                            province="Laguna", latitude=Decimal("14.27"), longitude=Decimal("121.12"))
b = Location.objects.create(street="B", barangay="Sala", city="Cabuyao",
                            province="Laguna", latitude=Decimal("14.25"), longitude=Decimal("121.10"))

# ── Four passengers sharing one ride ───────────────────────────
paxs = []
for i in range(4):
    u = User.objects.create_user(phone=f"0917000002{i}", password="t",
                                 full_name=f"Pasahero {i+1}", user_role=UserRole.PASSENGER)
    p = Passenger.objects.create(user=u, home_address="X", gcash_number=f"0917000002{i}")
    Wallet.objects.create(passenger=p, balance=Decimal("200.00"))
    paxs.append(p)

ride = Ride.objects.create(passenger=paxs[0], mode=tricycle, pickup_location=a,
                           dropoff_location=b, status=RideStatus.COMPLETED,
                           is_trip_chain=False)
RideLeg.objects.create(ride=ride, leg_no=1, mode=tricycle, origin_location=a,
                       dest_location=b, fare=Decimal("100.00"))
ride.recompute_chain_flags()

group = PakyawanGroup.objects.create(ride=ride, direction="Cabuyao → Sala", max_seats=4)

payment = Payment.objects.create(ride=ride, payer=paxs[0], method=gcash,
                                 amount=ride.final_fare, status=PaymentStatus.COMPLETED)

# ── The split: 100.00 across 4 must total exactly 100.00 ───────
total = payment.amount
count = len(paxs)
base = (total / count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
shares = [base] * count
# Push the rounding remainder onto the first passenger so the sum is exact.
shares[0] += total - (base * count)

for p, amt in zip(paxs, shares):
    FareShare.objects.create(payment=payment, passenger=p, group=group,
                             passenger_count=count, share_amount=amt)

recomputed = sum(s.share_amount for s in payment.shares.all())
print("fare:", total, "| shares:", [str(s) for s in shares], "| sum:", recomputed)
print("SPLIT BALANCES:", recomputed == total)               # True
```

**That rounding line is the whole lesson.** `100.00 / 3` is `33.333…`. Rounding each
share to `33.33` gives `99.99` — a centavo short, and a reconciliation report that
never balances. Pushing the remainder onto one share is the standard fix. Write this
down; it is exactly the kind of detail that reads as competence in a report.

Continue in the same shell:

```python
# ── 1. The composite key on FARE_SHARE ─────────────────────────
try:
    with transaction.atomic():
        FareShare.objects.create(payment=payment, passenger=paxs[0], group=group,
                                 passenger_count=count, share_amount=Decimal("1.00"))
    print("*** DUPLICATE SHARE ALLOWED ***")
except IntegrityError:
    print("duplicate (payment, passenger) rejected: True")

# ── 2. A negative share is rejected ────────────────────────────
try:
    with transaction.atomic():
        FareShare.objects.create(payment=payment, passenger=paxs[1], group=group,
                                 passenger_count=4, share_amount=Decimal("-5.00"))
    print("*** NEGATIVE SHARE ALLOWED ***")
except IntegrityError:
    print("negative share rejected: True")

# ── 3. Wallet balance cannot go negative ───────────────────────
w = paxs[0].wallet
try:
    with transaction.atomic():
        Wallet.objects.filter(pk=w.pk).update(balance=Decimal("-1.00"))
    print("*** NEGATIVE BALANCE ALLOWED ***")
except IntegrityError:
    print("negative wallet balance rejected: True")

# ── 4. A ledger entry moves the balance and records balance_after ──
before = w.balance
w.balance = before - Decimal("33.34")
w.save(update_fields=["balance", "updated_at"])
WalletTxn.objects.create(wallet=w, payment=payment, txn_type=TxnType.DEDUCT,
                         amount=Decimal("33.34"), balance_after=w.balance,
                         gateway_ref="SIM-W-0001")
w.refresh_from_db()
print("balance:", w.balance, "| ledger head:", w.transactions.first().balance_after)
print("LEDGER AGREES:", w.balance == w.transactions.first().balance_after)   # True

# ── 5. Receipt number generation ───────────────────────────────
r = Receipt.objects.create(payment=payment, total_amount=payment.amount,
                           receipt_no=Receipt.next_receipt_no())
print("receipt:", r.receipt_no)                              # SKY-<today>-0001
print("next:", Receipt.next_receipt_no())                    # SKY-<today>-0002

# ── 6. A ride has at most one payment (1 : 0..1) ───────────────
try:
    with transaction.atomic():
        Payment.objects.create(ride=ride, payer=paxs[0], method=cash,
                               amount=Decimal("0.00"))
    print("*** SECOND PAYMENT FOR ONE RIDE ALLOWED ***")
except IntegrityError:
    print("second payment for one ride rejected: True")
```

Continue:

```python
# ── 7. A payout is not a wallet transaction ────────────────────
drv_user = User.objects.create_user(phone="09170000030", password="t",
                                    full_name="Mang Ben", user_role=UserRole.DRIVER)
drv = Driver.objects.create(user=drv_user, license_number="N01-99-000001")
payout = DriverPayout.objects.create(driver=drv, method=gcash, amount=Decimal("90.00"),
                                     gateway_ref="SIM-P-0001")
print("payout status:", payout.status, "| settled:", payout.is_settled)
print("TxnType has PAYOUT?", "PAYOUT" in TxnType.values)      # False — by design

# ── 8. You cannot delete a wallet that has ledger entries ──────
try:
    with transaction.atomic():
        w.delete()
    print("*** WALLET WITH LEDGER DELETED ***")
except Exception as e:
    print("protected wallet delete rejected:", type(e).__name__)

# ── Clean up ───────────────────────────────────────────────────
Ride.objects.filter(pk=ride.pk).delete()
User.objects.filter(phone__startswith="0917000002").delete()
drv_user.delete()
Location.objects.filter(pk__in=[a.pk, b.pk]).delete()
exit()
```

### 5. Confirm in MySQL (~10 min)

```powershell
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW TABLES;"
docker compose exec mysql mysql -u sakayph -psakayph sakayph -e "SHOW CREATE TABLE FARE_SHARE\G"
```

Check `FARE_SHARE` for `UNIQUE KEY uq_fareshare_payment_passenger (payment_id, passenger_id)`.

### 6. Commit (~10 min)

```powershell
Set-Location ..
git add backend/apps/payments/
git commit -m "feat(payments): add wallet, payment, fare split, receipt and payout ledger"
git push
```

---

## Verify

- [ ] All seven models migrated
- [ ] `SHOW CREATE TABLE FARE_SHARE` shows the unique key on `(payment_id, passenger_id)`
- [ ] A four-way split of ₱100.00 sums to exactly ₱100.00, including a case that does not divide evenly
- [ ] A duplicate `(payment, passenger)` raises `IntegrityError`
- [ ] A negative share raises `IntegrityError`
- [ ] A negative wallet balance raises `IntegrityError`
- [ ] `WalletTxn.balance_after` matches the wallet balance after a deduction
- [ ] `Receipt.next_receipt_no()` returns `SKY-YYYYMMDD-0001`, then `-0002`
- [ ] A second payment for the same ride raises `IntegrityError`
- [ ] `TxnType` has no `PAYOUT` value
- [ ] Deleting a wallet with ledger entries is blocked
- [ ] Committed and pushed

---

## Log it

```markdown
**Step 2.06 — payment models — DONE**

- Added PAYMENT_METHOD, WALLET, PAYMENT, RECEIPT, FARE_SHARE, WALLET_TXN,
  DRIVER_PAYOUT
- WALLET has CHECK balance >= 0; FARE_SHARE has UNIQUE (payment, passenger)
- Split arithmetic uses ROUND_HALF_UP with the remainder pushed onto the first
  share, so shares total the fare exactly (100.00 / 3 case verified)
- Receipt numbers are SKY-YYYYMMDD-NNNN, generated from the last row
- Documented limitation: "shares sum to the fare" is a service-layer invariant,
  not a database constraint — SQL cannot assert a cross-row sum
- Verified 8 checks in shell; all constraints enforced
- **Commit:** <sha>
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `Cannot resolve keyword 'Payment'` | The string reference is misspelled | It must be `"Payment"` (same app) or `"payments.Payment"` |
| Split sums to ₱99.99 | Each share rounded independently | Push the remainder onto one share, as shown |
| `Receipt.next_receipt_no()` returns `-0001` every time | The `startswith` filter matches nothing because the date rolled over | Expected at midnight. The fallback to `1` is correct |
| `IntegrityError` on the second `Payment` for a ride | `PAYMENT.ride` is unique — working as designed | That is the 1 : 0..1. Use the existing payment |
| Cannot delete a wallet | `PROTECT` on `WalletTxn.wallet` | Correct — the ledger is the audit trail. Soft-delete instead |
| `ck_wallet_balance_nonneg` fires during a refund | The refund was written as a negative deduction | A refund is `TxnType.REFUND` with a positive amount that *increases* the balance |
| `decimal.InvalidOperation` on the split | `total / count` where count is an int | Wrap `count` in `Decimal(count)` |

---

## After this step

Money is modelled. One app left: the SOS Bantay tables, which is the smallest of the
five.

Next: [07 — Models: safety](07-models-safety.md)
