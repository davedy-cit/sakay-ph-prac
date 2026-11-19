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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="wallet_id")

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="payment_id")

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="txn_id")

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
    the database design: ``UC_Payout`` and ``payoutDriver(driverId, earnings)`` in
    the sequence diagram previously had no table to write to.

    Cannot be a WALLET_TXN row, because WALLET is passenger-scoped.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="payout_id")

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
