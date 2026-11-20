# Step 3.01 — JWT Auth and Simulated OTP

| | |
|---|---|
| **Goal** | Register (passenger + driver), login by phone, refresh, and `/api/auth/me/` work over JWT; the OTP code lives in Redis with a TTL — the frontend can exist after this step |
| **Day / Time** | Day 15 (Fri 20 Nov) · ~3 hours |
| **Status** | **DONE 20 November — 139 passed (122 Phase 2 + 17 new) at 88% coverage; full curl walk in §6 confirmed live** |
| **Prerequisites** | [Step 2.09](../phase-2-database/09-model-tests.md) — the test harness exists |
| **Produces** | `apps/accounts/{serializers,services,urls}.py`, a real `views.py`, `config/urls.py` wired, `tests/test_auth_api.py` |

---

## What this step is really doing

It is the first test of **the one hard rule of this phase**: views are thin, logic
lives in services. Registration is *two tables written atomically* (USER plus the
subtype profile) with a password policy and a uniqueness rule — none of which
belongs in a view. The OTP flow is a *Redis contract with a TTL* — again, a
service.

Two Phase 2 facts shape everything here:

- **`AUTH_USER_MODEL = "accounts.User"`, `USERNAME_FIELD = "phone"`.** SimpleJWT's
  `TokenObtainPairSerializer` reads `USERNAME_FIELD`, so the login body is
  `{"phone": ..., "password": ...}` with no override. `USER_ID_FIELD = "id"` is
  already in `settings.py` (Step 1.06); SimpleJWT 5.x casts the non-int UUID to a
  string for the token claim, and the lookup back through `pk=` works as-is.
- **`REST_FRAMEWORK`'s default permission is `IsAuthenticated`.** Every
  pre-authentication endpoint must declare `AllowAny` explicitly, or it 401s and
  looks like a broken token instead of a missing permission.

---

## Do this

### 1. The services (~45 min)

Create `backend/apps/accounts/services.py` — the views' entire brain:

```python
"""Account-domain services — the logic the views are thin wrappers over.

Registration writes two tables atomically (USER + its subtype profile) under a
password policy; the OTP flow is a Redis contract with a TTL. Neither belongs
in a view or a serializer.
"""

import secrets

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import Driver, Passenger, User
from apps.core.enums import UserRole


class RegistrationError(Exception):
    """A field-level registration failure the view turns into a 400."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(message)


class RegistrationService:
    """Creates a USER and its subtype profile in one transaction."""

    @staticmethod
    def register(*, phone: str, password: str, full_name: str, role: str,
                 **profile) -> User:
        if User.objects.filter(phone=phone).exists():
            raise RegistrationError("phone", "That phone number is already registered.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise RegistrationError("password", " ".join(exc.messages))

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    phone=phone, password=password, full_name=full_name, user_role=role,
                )
                if role == UserRole.PASSENGER:
                    Passenger.objects.create(
                        user=user,
                        home_address=profile["home_address"],
                        gcash_number=profile["gcash_number"],
                    )
                elif role == UserRole.DRIVER:
                    Driver.objects.create(user=user, license_number=profile["license_number"])
                else:
                    raise RegistrationError(
                        "role", "Self-registration is for passengers and drivers only."
                    )
        except KeyError as exc:
            # A missing profile field — the serializer should have caught it,
            # but the service owns the rule, so it re-checks.
            raise RegistrationError(exc.args[0], "This field is required.") from exc
        return user


class OtpError(Exception):
    """A non-field OTP failure, e.g. the re-send cooldown."""


class OtpService:
    """Simulated OTP — decision D-14.

    The code lives only in Redis under ``sakayph:otp:<phone>`` with a TTL from
    ``.env`` (``OTP_TTL_SECONDS``), never in MySQL: an OTP is ephemeral by
    definition, and Redis expires it without a cleanup job. A 60-second
    cooldown key stops a burst of re-sends. No SMS gateway is called — the
    code is returned to a DEBUG caller, which is what makes the flow
    demonstrable end to end.
    """

    KEY = "otp:{phone}"
    COOLDOWN_KEY = "otp-cooldown:{phone}"
    COOLDOWN_SECONDS = 60

    @classmethod
    def request_code(cls, phone: str) -> str:
        if cache.get(cls.COOLDOWN_KEY.format(phone=phone)):
            raise OtpError("Another code was sent recently. Wait a minute and retry.")
        code = f"{secrets.randbelow(1_000_000):06d}"
        cache.set(cls.KEY.format(phone=phone), code, settings.OTP_TTL_SECONDS)
        cache.set(cls.COOLDOWN_KEY.format(phone=phone), 1, cls.COOLDOWN_SECONDS)
        return code

    @classmethod
    def verify(cls, phone: str, code: str) -> bool:
        """One attempt per code: a correct code deletes itself on use."""
        key = cls.KEY.format(phone=phone)
        stored = cache.get(key)
        if stored is None or stored != code:
            return False
        cache.delete(key)
        return True
```

**Why the cache and not the database:** an OTP that outlives its usefulness
because a cron job forgot it is a self-inflicted bug. Redis' `EXPIRE` *is* the
TTL — `.env`'s `OTP_TTL_SECONDS` flows straight into `cache.set`, and Phase 2
already proved the cache lives on **db 1**, isolated from the channel layer.

### 2. The serializers (~30 min)

Create `backend/apps/accounts/serializers.py`:

```python
"""Account-API serializers.

A serializer validates input *shape*. The role-conditional "a driver needs a
license number" checks here are shape checks — the rules about *what a valid
account is* (password policy, uniqueness, profile creation) live in
RegistrationService.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import PHONE_VALIDATOR, User
from apps.core.enums import UserRole


class SakayTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login by phone (the USERNAME_FIELD) with domain claims in the payload."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["user_role"] = user.user_role
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": str(self.user.id),
            "phone": self.user.phone,
            "full_name": self.user.full_name,
            "user_role": self.user.user_role,
        }
        return data


class RegisterSerializer(serializers.Serializer):
    """Shape of a registration request. `role` picks the subtype profile."""

    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(min_length=8, write_only=True)
    full_name = serializers.CharField(max_length=120)
    role = serializers.ChoiceField(choices=[UserRole.PASSENGER, UserRole.DRIVER])

    home_address = serializers.CharField(max_length=255, required=False)
    gcash_number = serializers.CharField(max_length=15, required=False)
    license_number = serializers.CharField(max_length=30, required=False)

    def validate_phone(self, value):
        PHONE_VALIDATOR(value)  # raises ValidationError on a bad number
        return value

    def validate(self, attrs):
        role = attrs["role"]
        if role == UserRole.PASSENGER and not all(attrs.get(f) for f in ("home_address", "gcash_number")):
            raise serializers.ValidationError(
                {"home_address": "A passenger registration needs home_address and gcash_number."}
            )
        if role == UserRole.DRIVER and not attrs.get("license_number"):
            raise serializers.ValidationError(
                {"license_number": "A driver registration needs license_number."}
            )
        # Password policy is also shape here — the service re-checks it.
        # Wrapped so the 400 is keyed to `password`, not `non_field_errors`
        # (a bare validate_password inside validate() loses its field).
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs


class OtpRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)

    def validate_phone(self, value):
        PHONE_VALIDATOR(value)
        return value


class OtpVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(min_length=6, max_length=6)
```

### 3. The views and URLs (~30 min)

Replace `backend/apps/accounts/views.py` — every view is a wrapper:

```python
"""Account-API views. Thin wrappers over RegistrationService and OtpService."""

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.serializers import (
    OtpRequestSerializer, OtpVerifySerializer, RegisterSerializer,
    SakayTokenObtainPairSerializer,
)
from apps.accounts.services import OtpError, OtpService, RegistrationError, RegistrationService


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = RegistrationService.register(**serializer.validated_data)
        except RegistrationError as exc:
            return Response({exc.field: [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        refresh = SakayTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                "user": {"id": str(user.id), "phone": user.phone,
                         "full_name": user.full_name, "user_role": user.user_role},
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Phone + password in, JWT pair out. The default permission does not
    apply — SimpleJWT's own views ship AllowAny."""
    serializer_class = SakayTokenObtainPairSerializer


class MeView(APIView):
    """The authenticated caller's own account, with its subtype profile."""

    def get(self, request):
        user = request.user
        data = {
            "id": str(user.id), "phone": user.phone, "full_name": user.full_name,
            "user_role": user.user_role, "account_status": user.account_status,
        }
        if user.is_passenger:
            pax = user.passenger_profile
            data["profile"] = {"home_address": pax.home_address,
                               "gcash_number": pax.gcash_number}
        elif user.is_driver:
            drv = user.driver_profile
            data["profile"] = {"license_number": drv.license_number,
                               "accreditation_status": drv.accreditation_status,
                               "is_online": drv.is_online}
        return Response(data)


class OtpRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            code = OtpService.request_code(serializer.validated_data["phone"])
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        payload = {"detail": "A verification code was sent.", "expires_in": settings.OTP_TTL_SECONDS}
        # D-14: the simulated gateway hands the code back — but only in DEBUG,
        # so a production deployment never leaks codes into responses.
        if settings.DEBUG and settings.SIMULATE_OTP:
            payload["debug_code"] = code
        return Response(payload)


class OtpVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verified = OtpService.verify(**serializer.validated_data)
        if not verified:
            return Response({"code": ["Invalid or expired code."]},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"verified": True})
```

Refresh is SimpleJWT's stock `TokenRefreshView` — no customization needed.
Create `backend/apps/accounts/urls.py`:

```python
from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import (
    LoginView, MeView, OtpRequestView, OtpVerifyView, RegisterView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/otp/request/", OtpRequestView.as_view(), name="auth-otp-request"),
    path("auth/otp/verify/", OtpVerifyView.as_view(), name="auth-otp-verify"),
]
```

And wire it into `backend/config/urls.py` (replacing the stub):

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
]
```

### 4. The API tests (~45 min)

Create `backend/tests/test_auth_api.py`:

```python
"""Auth-API tests — Step 3.01's acceptance checks, over HTTP."""

from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.accounts.models import Driver, Passenger, User

PAX_PAYLOAD = {
    "phone": "09171110000", "password": "sakay-test-1234", "full_name": "Maria Santos",
    "role": "PASSENGER", "home_address": "12 Rizal St", "gcash_number": "09171110000",
}


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield


@pytest.fixture
def api():
    return APIClient()


def _register(api, **overrides):
    return api.post("/api/auth/register/", {**PAX_PAYLOAD, **overrides}, format="json")


# ── Registration ───────────────────────────────────────────────

def test_register_passenger_creates_user_and_profile(api, db):
    response = _register(api)
    assert response.status_code == 201, response.data
    assert "access" in response.data and "refresh" in response.data
    user = User.objects.get(phone=PAX_PAYLOAD["phone"])
    assert user.is_passenger
    assert Passenger.objects.filter(user=user).exists()


def test_register_driver_creates_driver_profile(api, db):
    # The passenger keys ride along unused — the service ignores them for a driver.
    response = _register(api, role="DRIVER", license_number="N01-11-111111")
    assert response.status_code == 201, response.data
    assert Driver.objects.filter(user__phone=PAX_PAYLOAD["phone"]).exists()


def test_register_rejects_a_duplicate_phone(api, db):
    assert _register(api).status_code == 201
    response = _register(api, full_name="Impostor")
    assert response.status_code == 400
    assert "phone" in response.data


def test_register_rejects_a_weak_password(api, db):
    response = _register(api, password="12345678")
    assert response.status_code == 400
    assert "password" in response.data


def test_register_rejects_a_malformed_phone(api, db):
    response = _register(api, phone="12345")
    assert response.status_code == 400


def test_register_admin_role_is_refused(api, db):
    response = _register(api, role="ADMIN")
    assert response.status_code == 400


# ── Login, refresh, me ─────────────────────────────────────────

def test_login_by_phone_returns_tokens_and_claims(api, db):
    _register(api)
    response = api.post("/api/auth/login/",
                        {"phone": PAX_PAYLOAD["phone"], "password": PAX_PAYLOAD["password"]},
                        format="json")
    assert response.status_code == 200
    assert response.data["user"]["user_role"] == "PASSENGER"


def test_access_token_opens_me(api, db):
    access = _register(api).data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.data["profile"]["home_address"] == "12 Rizal St"


def test_me_requires_authentication(api, db):
    assert api.get("/api/auth/me/").status_code == 401


def test_refresh_rotates_the_pair(api, db):
    refresh = _register(api).data["refresh"]
    response = api.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 200
    assert "access" in response.data


def test_suspended_user_cannot_login(api, db):
    _register(api)
    User.objects.filter(phone=PAX_PAYLOAD["phone"]).update(account_status="SUSPENDED")
    response = api.post("/api/auth/login/",
                        {"phone": PAX_PAYLOAD["phone"], "password": PAX_PAYLOAD["password"]},
                        format="json")
    assert response.status_code == 401


def test_wrong_password_is_a_401_not_a_500(api, db):
    _register(api)
    response = api.post("/api/auth/login/",
                        {"phone": PAX_PAYLOAD["phone"], "password": "wrong-password"}, format="json")
    assert response.status_code == 401


# ── OTP ────────────────────────────────────────────────────────

def test_otp_request_stores_a_code_in_redis(api, db):
    response = api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    assert response.status_code == 200
    assert response.data["expires_in"] > 0
    assert cache.get("otp:09172220000")  # six digits, sitting in Redis


def test_otp_request_enforces_the_cooldown(api, db):
    assert api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json").status_code == 200
    response = api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    assert response.status_code == 429


def test_otp_verify_accepts_and_consumes_the_code(api, db):
    api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    code = cache.get("otp:09172220000")
    assert api.post("/api/auth/otp/verify/", {"phone": "09172220000", "code": code}, format="json").status_code == 200
    # One attempt per code: verification consumed it.
    assert api.post("/api/auth/otp/verify/", {"phone": "09172220000", "code": code}, format="json").status_code == 400


def test_otp_verify_rejects_a_wrong_code(api, db):
    api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    response = api.post("/api/auth/otp/verify/", {"phone": "09172220000", "code": "000000"}, format="json")
    assert response.status_code == 400


def test_otp_verify_rejects_an_expired_code(api, db):
    api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    cache.delete("otp:09172220000")  # simulate the TTL elapsing
    response = api.post("/api/auth/otp/verify/", {"phone": "09172220000", "code": "123456"}, format="json")
    assert response.status_code == 400
```

Two things to notice in that file:

- **The autouse `clean_cache` fixture matters.** pytest-django rolls the
  *database* back between tests, but Redis is not a database — codes and
  cooldowns would leak from test to test. `cache.clear()` is the fixture that
  makes the OTP tests order-independent.
- **The tests never read a code out of a response.** `debug_code` only exists
  in DEBUG, and pytest runs with `DEBUG=False`, so the tests prove the real
  contract: the code is in Redis, and the response leaks nothing.

### 5. Run them (~15 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
pytest tests/test_auth_api.py -v
```

Expected: **17 passed**. Then the whole suite — Phase 2's 122 must still pass:

```powershell
pytest
```

Expected: **139 passed** (122 + 17).

### 6. Prove it over HTTP with curl (~10 min)

With `runserver` up (from a second terminal, per the setup guide), walk
register → me → OTP. PowerShell's `curl` is an alias for `Invoke-WebRequest`,
so use `curl.exe` explicitly, and the JSON body needs escaped quotes:

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/api/auth/register/ `
  -H "Content-Type: application/json" `
  -d '{\"phone\": \"09179990001\", \"password\": \"curl-demo-1234\", \"full_name\": \"Curl Demo\", \"role\": \"PASSENGER\", \"home_address\": \"12 Rizal St\", \"gcash_number\": \"09179990001\"}'
```

Copy the `access` value from the response and call `me` with it:

```powershell
curl.exe -s http://127.0.0.1:8000/api/auth/me/ -H "Authorization: Bearer <access-token>"
```

For OTP, request and verify **in one PowerShell command** — the code lives for
`OTP_TTL_SECONDS` (300 s), and separate tool/terminal rounds easily outlive it:

```powershell
$resp = curl.exe -s -X POST http://127.0.0.1:8000/api/auth/otp/request/ `
  -H "Content-Type: application/json" -d '{\"phone\": \"09179990002\"}'
$code = ($resp | ConvertFrom-Json).debug_code   # present only because DEBUG=True
curl.exe -s -X POST http://127.0.0.1:8000/api/auth/otp/verify/ `
  -H "Content-Type: application/json" -d ('{\"phone\": \"09179990002\", \"code\": \"' + $code + '\"}')
# → {"verified":true}; replaying the same code → 400 (one attempt per code)
```

Optional: eyeball the keys in Redis — note the real prefix is
`sakayph:1:<key>` (KEY_PREFIX : django version), and raw `redis-cli GET`
shows *pickled* bytes, not the plain code:

```powershell
docker exec sakayph-redis redis-cli -n 1 KEYS "*otp*"
```

This is the M3 habit starting early: every endpoint demonstrable without an
editor. Executed 20 November: register → me → OTP loop all confirmed live;
the one scare (a "vanished" code) was the 300 s TTL elapsing between manual
rounds, not a bug.

---

## Verify

- [ ] `pytest` → 139 passed (122 from Phase 2 + 17 new), 0 failures
- [ ] `/api/auth/register/` creates USER + Passenger (or Driver) atomically
- [ ] Login body is `phone`/`password`; the token carries `user_role`
- [ ] `/api/auth/me/` 401s without a token, 200s with one
- [ ] An OTP code is in Redis with a TTL, consumed on first verify
- [ ] A second OTP request inside 60 s gets 429
- [ ] No view contains registration or OTP logic

---

## Log it

In `steps/PROGRESS.md`, Day 15, and tick the overview's step table.

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| Register returns 401 | The default `IsAuthenticated` permission | `permission_classes = [AllowAny]` on every pre-auth view |
| `no such column: phone` or token lookup 500 | `USER_ID_FIELD` mis-set | It must be `"id"` (already in settings from Step 1.06) |
| OTP tests fail with a code left from a previous test | Redis is not rolled back | The autouse `clean_cache` fixture |
| `429` on the first OTP request of a test | Cooldown key leaked from another test | Same fixture |
| Login rejects a correct password | The user row's `account_status` is not ACTIVE | `is_active` is derived (Phase 2); suspend means no login, by design |
| `validate_password` rejects every test password | A validator wants non-numeric/similarity rules | Use `sakay-test-1234`-style passwords in fixtures |
| `ImportError: cannot import name 'validate_password' from 'django.core.validators'` | Guessed the module — it isn't there | `validate_password` lives in `django.contrib.auth.password_validation` |
| Weak-password 400 arrives as `non_field_errors` | `validate_password` raised bare inside `validate()` loses its field | Wrap it: `raise serializers.ValidationError({"password": list(exc.messages)})` |
| `TypeError: Object of type UUID is not JSON serializable` on login | Old SimpleJWT | The pinned 5.5.1 casts the UUID claim to a string — don't upgrade mid-phase |
| Hand-testing OTP: verify fails and the code "vanished" | The 300 s TTL elapsed between terminal rounds | Request and verify in one command (see §6) |
| `redis-cli GET` shows binary garbage instead of the code | django-redis pickles values | Read codes via `debug_code` or `cache.get`, never raw redis-cli |
| Redis key not found with pattern `sakayph:otp:*` | django-redis composes keys as `sakayph:1:<key>` (prefix : version) | Scan `*otp*` or use the full `sakayph:1:` prefix |

---

## After this step

DONE 20 November, commit `feat(api)`. The frontend has everything it needs to
sign people up. Next: **Step 3.02** — serializers, viewsets and the Swagger UI
at `/api/docs/`.
