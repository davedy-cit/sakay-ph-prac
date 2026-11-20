"""Ride-domain services — pure domain logic, no Django dependencies.

The FareCalculator is the single source of truth for fare arithmetic.
It takes a ride leg's mode and a distance, and returns a FareBreakdown
value object. No DB, no request, no clock — deterministic and testable.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from apps.rides.models import RideModeLookup


# ── Configuration ────────────────────────────────────────────────

# D-63: Platform takes 10% of the leg fare (after surge).
PLATFORM_FEE_RATE = Decimal("0.10")


# ── Value object ─────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class FareBreakdown:
    """Complete fare decomposition for one ride leg.

    Every field is a Decimal with two decimal places. The sum of
    platform_share + driver_share == leg_fare. For Pakyawan,
    passenger_share * seat_capacity + platform_share == leg_fare.
    """

    base_fare: Decimal
    distance_fare: Decimal
    booking_fee: Decimal
    subtotal: Decimal                 # base + distance + booking
    surge_multiplier: Decimal
    surge_amount: Decimal
    leg_fare: Decimal                 # subtotal * surge_multiplier
    platform_share: Decimal
    driver_share: Decimal
    passenger_share: Decimal          # per passenger if Pakyawan
    is_pakyawan: bool
    seat_capacity: int


# ── Calculator ───────────────────────────────────────────────────

class FareCalculator:
    """Stateless fare engine. All inputs are explicit — no hidden state."""

    def __init__(self, mode: RideModeLookup):
        self.mode = mode

    def compute(
        self,
        distance_km: Decimal,
        is_pakyawan: bool = False,
        surge_multiplier: Decimal = Decimal("1.00"),
    ) -> FareBreakdown:
        """
        Compute the full fare breakdown for one leg.

        Args:
            distance_km: The leg distance in kilometres (from the routing engine).
            is_pakyawan: True for a Pakyawan (shared) booking.
            surge_multiplier: 1.00 normally; > 1.00 during a Bagyo Mode window.

        Returns:
            A FareBreakdown with every component.
        """
        # 1. Base components from the mode row (D-62)
        base_fare = self.mode.base_fare
        per_km = self.mode.per_km_rate
        booking_fee = self.mode.booking_fee           # D-64: ₱3.00
        seat_capacity = self.mode.seat_capacity

        # 2. Distance fare
        distance_fare = (distance_km * per_km).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 3. Subtotal before surge
        subtotal = (base_fare + distance_fare + booking_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 4. Surge (D-66) — applies to the whole leg fare including booking_fee
        surge_multiplier = surge_multiplier.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        leg_fare = (subtotal * surge_multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        surge_amount = (leg_fare - subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 5. Platform / driver split (D-63)
        platform_share = (leg_fare * PLATFORM_FEE_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        driver_share = (leg_fare - platform_share).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 6. Passenger share — Pakyawan divides driver_share equally
        if is_pakyawan:
            # Integer division with remainder to the last passenger
            per_passenger = (driver_share / seat_capacity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            # The last passenger pays the remainder so the sum is exact
            passenger_share = per_passenger
        else:
            passenger_share = leg_fare

        return FareBreakdown(
            base_fare=base_fare,
            distance_fare=distance_fare,
            booking_fee=booking_fee,
            subtotal=subtotal,
            surge_multiplier=surge_multiplier,
            surge_amount=surge_amount,
            leg_fare=leg_fare,
            platform_share=platform_share,
            driver_share=driver_share,
            passenger_share=passenger_share,
            is_pakyawan=is_pakyawan,
            seat_capacity=seat_capacity,
        )