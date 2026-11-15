"""Tunable business constants.

Values that a real operator would change without a code deploy belong in
PLATFORM_CONFIG (a database table). Values that are structural belong here.
"""

from decimal import Decimal

# ── Matching ───────────────────────────────────────────────────
DEFAULT_SEARCH_RADIUS_KM = 3.0
MATCH_TIMEOUT_SECONDS = 90
MAX_CHAIN_LEGS = 4

# ── Money ──────────────────────────────────────────────────────
CURRENCY = "PHP"

# ── Simulated providers ────────────────────────────────────────
# No real gateway, SMS provider or GPS hardware is used anywhere in this
# project. These keep that visible in the code rather than implied.
SIMULATED_GATEWAY_PREFIX = "SIM-"
SIMULATED_OTP_LENGTH = 6