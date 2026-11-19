# Step 2.06 §4 — prove the money models behave.
# Step file's shell block minus the REPL `exit()`, plus the uneven-split case
# the verify checklist asks for (₱100 across 3 — a centavo-rounding trap).
from decimal import Decimal, ROUND_HALF_UP
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Driver, Passenger, User
from apps.core.enums import PaymentMethod, PaymentStatus, RideMode, RideStatus, UserRole, TxnType
from apps.payments.models import (
    DriverPayout, FareShare, Payment, PaymentMethodLookup, Receipt, Wallet, WalletTxn,
)
from apps.rides.models import Location, PakyawanGroup, Ride, RideLeg, RideModeLookup

# ── Lookups ────────────────────────────────────────────────────
gcash, _ = PaymentMethodLookup.objects.get_or_create(
    method_code=PaymentMethod.GCASH,
    defaults=dict(method_name="GCash", is_digital=True, gateway_name="GCash"))
cash, _ = PaymentMethodLookup.objects.get_or_create(
    method_code=PaymentMethod.CASH,
    defaults=dict(method_name="Cash", is_digital=False))

tricycle, _ = RideModeLookup.objects.get_or_create(
    mode_code=RideMode.TRICYCLE,
    defaults=dict(mode_name="Tricycle", base_fare=Decimal("25.00"),
                  per_km_rate=Decimal("12.00"), seat_capacity=3, is_shared=False),
)

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

# ── The uneven case the checklist asks for: 100.00 across 3 ────
pax3 = []
for i in range(3):
    u = User.objects.create_user(phone=f"0917000004{i}", password="t",
                                 full_name=f"Tresharer {i+1}", user_role=UserRole.PASSENGER)
    p = Passenger.objects.create(user=u, home_address="X", gcash_number=f"0917000004{i}")
    pax3.append(p)
ride3 = Ride.objects.create(passenger=pax3[0], mode=tricycle, pickup_location=a,
                            dropoff_location=b, status=RideStatus.COMPLETED)
RideLeg.objects.create(ride=ride3, leg_no=1, mode=tricycle, origin_location=a,
                       dest_location=b, fare=Decimal("100.00"))
ride3.recompute_chain_flags()
payment3 = Payment.objects.create(ride=ride3, payer=pax3[0], method=gcash,
                                  amount=ride3.final_fare, status=PaymentStatus.COMPLETED)
count3 = 3
base3 = (payment3.amount / count3).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
shares3 = [base3] * count3
shares3[0] += payment3.amount - (base3 * count3)
for p, amt in zip(pax3, shares3):
    FareShare.objects.create(payment=payment3, passenger=p, group=group,
                             passenger_count=count3, share_amount=amt)
recomputed3 = sum(s.share_amount for s in payment3.shares.all())
print("uneven fare:", payment3.amount, "| shares:", [str(s) for s in shares3],
      "| sum:", recomputed3)
print("UNEVEN SPLIT BALANCES:", recomputed3 == payment3.amount)   # True

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
# PROTECT-aware order: Payment.ride and PakyawanGroup.ride are PROTECT, so
# payments (and their receipt) must go before the ride; WalletTxn.wallet is
# PROTECT, so the ledger goes before the users (whose cascade would take the
# wallets). FareShare cascades with its payment.
Receipt.objects.filter(payment__ride_id__in=[ride.pk, ride3.pk]).delete()
Payment.objects.filter(ride_id__in=[ride.pk, ride3.pk]).delete()
WalletTxn.objects.filter(wallet__passenger__user__phone__startswith="0917000002").delete()
DriverPayout.objects.filter(driver__user__phone__in=["09170000030"]).delete()
Ride.objects.filter(pk__in=[ride.pk, ride3.pk]).delete()
User.objects.filter(phone__startswith="0917000002").delete()
User.objects.filter(phone__startswith="0917000004").delete()
User.objects.filter(phone__in=["09170000030"]).delete()
Location.objects.filter(pk__in=[a.pk, b.pk]).delete()
