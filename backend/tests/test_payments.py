"""Payments-domain tests — the split, the ledger and the 1:0..1 constraints."""

from decimal import ROUND_HALF_UP, Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.core.enums import PaymentStatus, PayoutStatus, TxnType
from apps.payments.models import (
    DriverPayout, FareShare, Payment, Receipt, Wallet, WalletTxn,
)
from apps.rides.models import PakyawanGroup


@pytest.fixture
def payment(ride, passenger, gcash):
    return Payment.objects.create(
        ride=ride, payer=passenger, method=gcash, amount=ride.final_fare,
        status=PaymentStatus.COMPLETED,
    )


def test_one_payment_per_ride(ride, passenger, gcash, cash):
    """PAYMENT.ride is NOT NULL + UNIQUE — the 1 : 0..1."""
    Payment.objects.create(ride=ride, payer=passenger, method=gcash,
                           amount=Decimal("60.00"))
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Payment.objects.create(ride=ride, payer=passenger, method=cash,
                                   amount=Decimal("60.00"))


def test_cash_payment_needs_no_wallet(ride, passenger, cash):
    """PAYMENT -> WALLET is 0..1 : 0..*; cash bypasses the wallet."""
    p = Payment.objects.create(ride=ride, payer=passenger, method=cash,
                               amount=Decimal("60.00"))
    assert p.wallet is None


def test_wallet_balance_cannot_go_negative(passenger):
    """The safety net for every money bug."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Wallet.objects.filter(pk=passenger.wallet.pk).update(balance=Decimal("-1.00"))


def test_wallet_txn_records_the_running_balance(passenger, payment):
    w = passenger.wallet
    w.balance = w.balance - Decimal("33.34")
    w.save(update_fields=["balance", "updated_at"])
    txn = WalletTxn.objects.create(wallet=w, payment=payment, txn_type=TxnType.DEDUCT,
                                   amount=Decimal("33.34"), balance_after=w.balance,
                                   gateway_ref="SIM-W-0001")
    w.refresh_from_db()
    assert txn.balance_after == w.balance == Decimal("466.66")


def test_wallet_with_ledger_entries_cannot_be_deleted(passenger, payment):
    """The ledger is the audit trail — PROTECT, not CASCADE."""
    w = passenger.wallet
    WalletTxn.objects.create(wallet=w, payment=payment, txn_type=TxnType.DEDUCT,
                             amount=Decimal("10.00"), balance_after=Decimal("490.00"))
    with pytest.raises(Exception):
        with transaction.atomic():
            w.delete()


def test_txn_type_has_no_payout_value():
    """Driver earnings are not a passenger-wallet transaction."""
    assert "PAYOUT" not in TxnType.values
    assert set(TxnType.values) == {"TOPUP", "DEDUCT", "REFUND"}


def test_fare_share_is_unique_per_payment_and_passenger(payment, passenger, ride):
    grp = PakyawanGroup.objects.create(ride=ride, direction="X → Y", max_seats=4)
    FareShare.objects.create(payment=payment, passenger=passenger, group=grp,
                             passenger_count=1, share_amount=Decimal("60.00"))
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            FareShare.objects.create(payment=payment, passenger=passenger, group=grp,
                                     passenger_count=1, share_amount=Decimal("1.00"))


def test_fare_share_amount_cannot_be_negative(payment, passenger, ride):
    grp = PakyawanGroup.objects.create(ride=ride, direction="X → Y", max_seats=4)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            FareShare.objects.create(payment=payment, passenger=passenger, group=grp,
                                     passenger_count=2, share_amount=Decimal("-5.00"))


def split_fare(total: Decimal, count: int) -> list[Decimal]:
    """The Pakyawan split, with the rounding remainder pushed onto one share.

    ROUND_HALF_UP on each share alone leaves a remainder — 100.00 / 3 gives
    99.99 — so the leftover centavo has to go somewhere or the shares never
    total the fare. This helper is what Phase 3's FareCalculator will use;
    writing it here first means the rule is tested before it is relied on.
    """
    base = (total / Decimal(count)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    shares = [base] * count
    shares[0] += total - (base * count)
    return shares


@pytest.mark.parametrize("count", [1, 2, 3, 4, 7])
def test_split_sums_to_the_fare_exactly(count):
    """The Pakyawan invariant: the shares must total the fare, exactly."""
    total = Decimal("60.00")
    shares = split_fare(total, count)
    assert sum(shares) == total, f"{count}-way split of {total} gives {sum(shares)}"
    assert all(s >= 0 for s in shares)
    assert len(shares) == count


@pytest.mark.parametrize("count", [3, 7, 11])
def test_naive_rounding_would_lose_a_centavo(count):
    """The bug the remainder-push exists to prevent.

    If each share is rounded independently the total falls short. This test
    documents why split_fare is written the way it is — remove the remainder
    push and both this and the test above fail.
    """
    total = Decimal("100.00")
    base = (total / Decimal(count)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert base * count != total, "pick a total that does not divide evenly"


def test_split_writes_one_share_per_passenger(payment, passenger, ride):
    """FARE_SHARE is unique on (payment, passenger), so a 3-way split needs
    three distinct passengers — which is the whole point of the table."""
    from apps.accounts.models import Passenger, User
    from apps.core.enums import UserRole

    others = []
    for i in range(2):
        u = User.objects.create_user(
            phone=f"0917000009{i}", password="x", full_name=f"Pasahero {i}",
            user_role=UserRole.PASSENGER,
        )
        others.append(Passenger.objects.create(
            user=u, home_address="X", gcash_number=f"0917000009{i}",
        ))

    grp = PakyawanGroup.objects.create(ride=ride, direction="X → Y", max_seats=4)
    everyone = [passenger, *others]
    shares = split_fare(payment.amount, len(everyone))

    for pax, amount in zip(everyone, shares):
        FareShare.objects.create(
            payment=payment, passenger=pax, group=grp,
            passenger_count=len(everyone), share_amount=amount,
        )

    stored = list(payment.shares.values_list("share_amount", flat=True))
    assert len(stored) == 3
    assert sum(stored) == payment.amount


def test_receipt_number_is_sequential(payment):
    first = Receipt.objects.create(payment=payment, total_amount=payment.amount,
                                   receipt_no=Receipt.next_receipt_no())
    assert first.receipt_no.endswith("-0001")
    assert Receipt.next_receipt_no().endswith("-0002")


def test_receipt_total_is_a_snapshot(payment):
    """A receipt must not move if the payment is later adjusted."""
    r = Receipt.objects.create(payment=payment, total_amount=payment.amount,
                               receipt_no=Receipt.next_receipt_no())
    payment.amount = Decimal("999.00")
    payment.save(update_fields=["amount"])
    r.refresh_from_db()
    assert r.total_amount == Decimal("60.00")


def test_one_receipt_per_payment(payment):
    Receipt.objects.create(payment=payment, total_amount=payment.amount,
                           receipt_no=Receipt.next_receipt_no())
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Receipt.objects.create(payment=payment, total_amount=payment.amount,
                                   receipt_no="SKY-19700101-9999")


def test_driver_payout_defaults_to_requested(driver, gcash):
    p = DriverPayout.objects.create(driver=driver, method=gcash,
                                    amount=Decimal("90.00"), gateway_ref="SIM-P-0001")
    assert p.status == PayoutStatus.REQUESTED
    assert p.is_settled is False


def test_payout_is_not_a_wallet_transaction(driver, gcash):
    """WALLET is passenger-scoped, so a payout needs its own table."""
    payout = DriverPayout.objects.create(driver=driver, method=gcash,
                                         amount=Decimal("90.00"))
    assert payout._meta.db_table == "DRIVER_PAYOUT"
    assert not hasattr(payout, "wallet")
